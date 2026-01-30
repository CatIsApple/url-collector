"""Groq AI를 사용한 URL 필터링"""

import os
import re
import requests
from typing import Optional
from urllib.parse import urlparse, unquote, parse_qs


def is_obvious_post(url: str) -> bool:
    """규칙 기반으로 명확한 게시글 URL 판별"""
    parsed = urlparse(url)
    path = unquote(parsed.path).rstrip("/")
    query = parsed.query

    # 게시글/페이지네이션 관련 파라미터가 있으면 POST
    post_params = ["wr_id", "spt", "sca", "sst", "sod", "sop", "stx", "sfl", "page"]
    if any(p + "=" in query for p in post_params):
        return True

    # 경로 세그먼트 분석
    segments = [s for s in path.split("/") if s and not s.endswith(".php")]

    # /category/숫자 형태는 POST (예: /mt/5733, /event/219)
    if len(segments) >= 2 and re.match(r'^\d+$', segments[-1]):
        return True

    # 긴 한글 제목 패턴 (하이픈으로 연결된 긴 문장)
    # 예: /먹튀-사이트-유형별-특징과-예방법/
    if len(segments) >= 2:
        last_segment = segments[-1]
        # 하이픈이 3개 이상이고 길이가 20자 이상이면 게시글 제목
        if last_segment.count("-") >= 3 and len(last_segment) > 20:
            return True
        # 한글이 포함되고 하이픈이 2개 이상이면 게시글
        if re.search(r'[가-힣]', last_segment) and last_segment.count("-") >= 2:
            return True

    # 숫자로만 된 세그먼트가 있으면 POST (게시글 ID)
    for seg in segments:
        if re.match(r'^\d+$', seg) and len(seg) >= 2:
            return True

    return False


def is_obvious_seo(url: str) -> bool:
    """규칙 기반으로 명확한 SEO 페이지 판별 (매우 엄격하게)"""
    parsed = urlparse(url)
    path = unquote(parsed.path).rstrip("/")
    query = parsed.query

    # 쿼리 파라미터가 있으면 대부분 POST (페이지네이션 등)
    if query:
        # 순수 bo_table만 있는 경우만 SEO
        if "board.php" in path and "bo_table=" in query:
            # page, wr_id 등 다른 파라미터 있으면 POST
            exclude_params = ["wr_id", "sca", "spt", "sst", "sod", "sop", "stx", "sfl", "page"]
            if any(p + "=" in query for p in exclude_params):
                return False
            # bo_table만 있는 경우만 SEO
            if query.count("=") == 1:
                return True
        return False

    # 루트 페이지
    if not path or path == "/":
        return True

    # 경로 세그먼트 분석
    segments = [s for s in path.split("/") if s and not s.endswith(".php")]

    # .php 파일이 있으면 AI에게 맡김
    if ".php" in path:
        return False

    # 단일 세그먼트 카테고리만 SEO (예: /free, /notice, /event)
    if len(segments) == 1:
        segment = segments[0]
        # 순수 숫자가 아니고, 짧은 이름이면 SEO
        if not re.match(r'^\d+$', segment) and len(segment) <= 15:
            return True

    return False


class GroqFilter:
    """Groq API를 사용하여 URL이 SEO 페이지인지 게시글인지 판단"""

    API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._load_api_key()
        if not self.api_key:
            raise ValueError("Groq API 키가 필요합니다")

    def _load_api_key(self) -> Optional[str]:
        """API 키 로드"""
        key = os.environ.get("GROQ_API_KEY")
        if key:
            return key
        config_path = os.path.expanduser("~/.groq-api-key")
        if os.path.exists(config_path):
            with open(config_path) as f:
                return f.read().strip()
        return None

    def classify_urls(self, urls: list[str], batch_size: int = 20) -> dict[str, str]:
        """URL 목록을 SEO/POST로 분류"""
        results = {}
        need_ai = []

        # 1단계: 규칙 기반 사전 필터링
        for url in urls:
            if is_obvious_post(url):
                results[url] = "POST"
            elif is_obvious_seo(url):
                results[url] = "SEO"
            else:
                need_ai.append(url)

        print(f"[필터] 규칙 기반: SEO {sum(1 for v in results.values() if v=='SEO')}개, POST {sum(1 for v in results.values() if v=='POST')}개, AI 필요 {len(need_ai)}개")

        # 2단계: AI로 나머지 분류
        if need_ai:
            for i in range(0, len(need_ai), batch_size):
                batch = need_ai[i:i + batch_size]
                batch_results = self._classify_batch(batch)
                results.update(batch_results)

        return results

    def _classify_batch(self, urls: list[str]) -> dict[str, str]:
        """URL 배치 분류"""
        prompt = """URL을 SEO(카테고리 페이지) 또는 POST(개별 게시글)로 분류해.

SEO 예시 (메뉴/카테고리 - 이런 URL만 유지):
- / (메인)
- /free /notice /event /review (카테고리)
- /자유게시판/ /공지사항/ /먹튀제보/ (한글 카테고리)
- /bbs/board.php?bo_table=notice (게시판 목록)
- /login/ /register/ /profile/ (회원 페이지)

POST 예시 (게시글 - 필터링 대상):
- /mt/5733 /event/219 (숫자로 끝남)
- /먹튀-사이트-유형별-특징/ (긴 제목, 하이픈 많음)
- /bsite/body-바디-먹튀-검증/ (게시글 제목)
- ?wr_id=123 (글 ID)

중요: 의심되면 POST로 분류. SEO는 확실한 카테고리만.

URL 목록:
"""
        for i, url in enumerate(urls, 1):
            prompt += f"{i}. {url}\n"

        prompt += "\n각 번호에 SEO 또는 POST만 답변:"

        try:
            resp = requests.post(
                self.API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Accept-Encoding": "identity"
                },
                json={
                    "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "max_tokens": 300
                },
                timeout=30
            )

            if resp.status_code != 200:
                print(f"[ERR] Groq API 상태: {resp.status_code}")
                # API 에러시 POST로 처리 (안전하게)
                return {url: "POST" for url in urls}

            data = resp.json()
            answer = data["choices"][0]["message"]["content"]

            result = self._parse_response(urls, answer)
            seo_count = sum(1 for v in result.values() if v == "SEO")
            print(f"[AI] 배치 {len(urls)}개 중 SEO: {seo_count}개, POST: {len(urls)-seo_count}개")
            return result

        except Exception as e:
            print(f"[ERR] Groq API 오류: {e}")
            # 에러시 POST로 처리 (안전하게)
            return {url: "POST" for url in urls}

    def _parse_response(self, urls: list[str], answer: str) -> dict[str, str]:
        """AI 응답 파싱"""
        results = {}
        lines = answer.strip().split("\n")

        for i, url in enumerate(urls):
            # 기본값은 POST (안전하게 필터링)
            classification = "POST"

            # 해당 번호로 시작하는 줄 찾기
            for line in lines:
                line_stripped = line.strip()
                if line_stripped.startswith(f"{i+1}.") or line_stripped.startswith(f"{i+1} "):
                    # SEO라고 명시된 경우만 SEO
                    if "SEO" in line.upper():
                        classification = "SEO"
                    break

            results[url] = classification

        return results

    def filter_seo_urls(self, urls: list[str]) -> list[str]:
        """SEO 페이지만 필터링하여 반환"""
        if not urls:
            return []

        classifications = self.classify_urls(urls)
        return [url for url, cls in classifications.items() if cls == "SEO"]


def remove_page_param(url: str) -> str:
    """URL에서 page 파라미터 제거"""
    parsed = urlparse(url)
    query = parsed.query

    if not query:
        return url

    # page 파라미터 제거
    params = parse_qs(query, keep_blank_values=True)
    params.pop('page', None)

    # 쿼리 재구성
    new_query = "&".join(f"{k}={v[0]}" for k, v in params.items() if v)

    # URL 재구성
    if new_query:
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"
    else:
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def extract_category_urls(urls: list[dict]) -> list[dict]:
    """게시글 URL에서 카테고리 URL 추출"""
    categories = set()
    domain = None

    for item in urls:
        url = item["url"]
        parsed = urlparse(url)

        if not domain:
            domain = f"{parsed.scheme}://{parsed.netloc}"

        query = parsed.query
        if not query:
            continue

        # bo_table 파라미터 추출
        params = parse_qs(query)
        if "bo_table" in params:
            bo_table = params["bo_table"][0]
            categories.add(bo_table)

    # 카테고리 URL 생성
    result = []
    for cat in sorted(categories):
        cat_url = f"{domain}/bbs/board.php?bo_table={cat}"
        result.append({
            "url": cat_url,
            "title": f"{cat} 게시판",
            "snippet": "",
            "domain": urlparse(domain).netloc if domain else "",
        })

    return result


def filter_urls_with_ai(urls: list[dict], api_key: Optional[str] = None) -> list[dict]:
    """AI를 사용하여 SEO 페이지만 필터링"""
    if not urls:
        return []

    url_list = [item["url"] for item in urls]

    try:
        groq = GroqFilter(api_key)
        classifications = groq.classify_urls(url_list)
    except Exception as e:
        print(f"[WARN] AI 필터링 실패, 규칙 기반만 적용: {e}")
        # API 실패 시 규칙 기반만으로 분류
        classifications = {}
        for url in url_list:
            if is_obvious_post(url):
                classifications[url] = "POST"
            elif is_obvious_seo(url):
                classifications[url] = "SEO"
            else:
                # 불확실하면 POST로 처리 (안전하게)
                classifications[url] = "POST"

    # SEO로 분류된 것만 필터링
    seo_items = [item for item in urls if classifications.get(item["url"]) == "SEO"]

    # 게시글에서 카테고리 URL 추출 (wr_id 있는 URL에서 bo_table 추출)
    category_urls = extract_category_urls(urls)

    # 기존 SEO + 추출된 카테고리 병합
    all_seo = seo_items + category_urls

    # page 파라미터 제거 및 중복 제거
    seen_urls = set()
    result = []
    for item in all_seo:
        clean_url = remove_page_param(item["url"])
        if clean_url not in seen_urls:
            seen_urls.add(clean_url)
            item["url"] = clean_url  # URL 업데이트
            result.append(item)

    return result


if __name__ == "__main__":
    test_urls = [
        "https://mt-to.com/",
        "https://mt-to.com/bsite",
        "https://mt-to.com/security",
        "https://mt-to.com/bbs/board.php?bo_table=notice",
        "https://mt-to.com/notice/트러스트-제휴종료/?page=11",
        "https://mt-to.com/bsite/body-바디-먹튀-body-2020com-먹튀검증-25만원/",
    ]

    groq = GroqFilter()
    results = groq.classify_urls(test_urls)

    print("\n분류 결과:")
    for url, cls in results.items():
        print(f"  [{cls:4s}] {url[:70]}")
