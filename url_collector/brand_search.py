"""업체명 기반 검색 - 구글에서 브랜드명으로 검색하여 SEO 페이지 수집"""

import re
import requests
from urllib.parse import urlparse, unquote


class BrandSearcher:
    """브랜드/업체명으로 구글 검색하여 관련 페이지 수집"""

    SERPER_URL = "https://google.serper.dev/search"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
            "Accept-Encoding": "identity"  # 압축 해제 오류 방지
        })

    def extract_brand_name(self, domain: str) -> str:
        """도메인에서 브랜드명 추출"""
        # http/https 제거
        domain = domain.replace("https://", "").replace("http://", "")
        domain = domain.split("/")[0]  # 경로 제거

        # www 제거
        if domain.startswith("www."):
            domain = domain[4:]

        # TLD 제거
        name = domain.split(".")[0]

        # 숫자 제거 (mtgal08 -> mtgal)
        name = re.sub(r'\d+$', '', name)

        return name

    def get_site_title(self, domain: str) -> str | None:
        """사이트 메인 페이지에서 타이틀 추출 (브랜드명)"""
        try:
            # site: 검색으로 메인/홈 페이지 정보 가져오기
            resp = self.session.post(
                self.SERPER_URL,
                json={
                    "q": f"site:{domain}",
                    "gl": "kr",
                    "hl": "ko",
                    "num": 10  # 여러 개 가져와서 메인 페이지 찾기
                },
                timeout=10
            )
            if resp.status_code != 200:
                return None

            data = resp.json()
            organic = data.get("organic", [])
            if not organic:
                return None

            # 브랜드 후보 수집
            brand_candidates = {}

            for item in organic:
                title = item.get("title", "")
                url = item.get("link", "")
                path = urlparse(url).path.rstrip("/")

                # "제목 > 카테고리" 형식에서 카테고리 제거
                if " > " in title:
                    title = title.split(" > ")[0].strip()

                # 구분자로 분리하여 브랜드 후보 추출
                separators = [" - ", " | ", " : ", ": ", ":"]
                parts = [title]
                for sep in separators:
                    if sep in title:
                        parts = [p.strip() for p in title.split(sep)]
                        break

                for part in parts:
                    # 브랜드명 정리
                    brand = self._clean_brand_name(part)
                    if brand and 2 <= len(brand) <= 10:
                        # 메인 페이지면 가중치 높임
                        weight = 3 if path in ["", "/", "/show", "/index.php", "/main", "/home"] else 1
                        brand_candidates[brand] = brand_candidates.get(brand, 0) + weight

            # 가장 많이 나온 브랜드 선택 (단, 일반적인 단어 제외)
            generic_words = {"먹튀검증", "먹튀신고", "토토사이트", "안전놀이터", "카지노", "먹튀", "토토", "검증", "사이트"}
            # 브랜드로 부적합한 단어 (일반 명사/동사/콘텐츠 제목)
            bad_brands = {
                "충전방법", "이벤트", "공지사항", "로그인", "회원가입", "게시판", "분석픽", "스포츠",
                "라이온", "자유게시판", "먹튀사이트", "신고", "제보", "안내", "소개"
            }

            def is_likely_brand(text: str) -> bool:
                """브랜드명으로 적합한지 판단"""
                if not text:
                    return False
                # 공백 포함 = 콘텐츠 제목 가능성 높음
                if " " in text:
                    return False
                # 너무 짧거나 길면 부적합
                if len(text) < 2 or len(text) > 10:
                    return False
                # "는", "은", "가" 등 조사로 끝나면 콘텐츠 제목 (단, "데이", "토이" 등 영어 음차 제외)
                if re.search(r'[는은가을를의]$', text) and not re.search(r'(데이|토이|키|비)$', text):
                    return False
                # 영문+하이픈+숫자 패턴 (U-20, K-1 등) = 콘텐츠 제목
                if re.search(r'^[A-Za-z]+-\d+', text):
                    return False
                # 숫자로만 시작하면 부적합
                if re.search(r'^\d', text):
                    return False
                # 일반 단어면 부적합
                if text in generic_words or text in bad_brands:
                    return False
                return True

            best_brand = None
            best_score = 0
            for brand, score in brand_candidates.items():
                # 브랜드로 부적합하면 건너뜀
                if not is_likely_brand(brand):
                    continue
                # 짧은 브랜드명 선호 (2-6글자)
                if 2 <= len(brand) <= 6:
                    score = score * 1.5
                if score > best_score:
                    best_score = score
                    best_brand = brand

            # site: 검색으로 좋은 브랜드 못 찾으면 도메인명 검색 시도
            should_fallback = (
                not best_brand or
                best_brand in generic_words or
                best_brand in bad_brands or
                " " in (best_brand or "") or
                best_score < 2
            )

            if should_fallback:
                domain_brand = self.get_brand_from_domain_search(domain)
                if domain_brand:
                    return domain_brand

            # 여전히 일반 단어면 None 반환 (도메인으로 fallback하도록)
            if best_brand in generic_words:
                return None

            return best_brand

        except:
            return None

    def _clean_brand_name(self, text: str) -> str | None:
        """브랜드명 정리"""
        if not text:
            return None

        # 앞뒤 특수문자 제거 (괄호류 포함)
        text = re.sub(r'^[\s\-\|:【】\[\]()（）「」『』]+', '', text)
        text = re.sub(r'[\s\-\|:【】\[\]()（）「」『』]+$', '', text)

        # "..." 포함시 제외
        if "..." in text:
            return None

        # 너무 긴 텍스트는 첫 단어만
        if len(text) > 15:
            words = text.split()
            if words:
                text = words[0]

        # 다시 정리
        text = re.sub(r'^[\s\-\|:【】\[\]]+', '', text)
        text = re.sub(r'[\s\-\|:【】\[\]]+$', '', text)

        return text if text else None

    def get_brand_from_domain_search(self, domain: str) -> str | None:
        """도메인명으로 검색하여 브랜드 추출"""
        try:
            # 도메인에서 핵심 이름 추출 (예: mtgal.com -> mtgal)
            domain_clean = domain.replace("www.", "")
            domain_name = self.extract_brand_name(domain)

            resp = self.session.post(
                self.SERPER_URL,
                json={
                    "q": f'"{domain_name}"',
                    "gl": "kr",
                    "hl": "ko",
                    "num": 10
                },
                timeout=10
            )
            if resp.status_code != 200:
                return None

            data = resp.json()
            organic = data.get("organic", [])

            # 타겟 도메인의 결과에서 브랜드 추출
            for item in organic:
                url = item.get("link", "")
                # 해당 도메인 URL인지 확인
                if domain_clean not in url:
                    continue

                title = item.get("title", "")
                # "브랜드명 - 설명" 형식
                if " - " in title:
                    brand = title.split(" - ")[0].strip()
                    brand = self._clean_brand_name(brand)
                    if brand and 2 <= len(brand) <= 10:
                        return brand
                # "브랜드명 | 설명" 형식
                elif " | " in title:
                    brand = title.split(" | ")[0].strip()
                    brand = self._clean_brand_name(brand)
                    if brand and 2 <= len(brand) <= 10:
                        return brand

            return None
        except:
            return None

    def search_brand(
        self,
        brand_name: str,
        num_results: int = 50,
        include_related: bool = True
    ) -> list[dict]:
        """
        브랜드명으로 구글 검색

        Args:
            brand_name: 검색할 브랜드명 (예: "먹튀갤", "mtgal")
            num_results: 최대 결과 수
            include_related: 관련 사이트도 포함할지

        Returns:
            [{"url": ..., "title": ..., "snippet": ..., "domain": ...}, ...]
        """
        all_results = []
        seen_urls = set()
        page = 1
        per_page = 10

        # 검색어: 브랜드명 (정확한 매칭을 위해 따옴표)
        query = f'"{brand_name}"'

        while len(all_results) < num_results and page <= 10:
            try:
                resp = self.session.post(
                    self.SERPER_URL,
                    json={
                        "q": query,
                        "gl": "kr",
                        "hl": "ko",
                        "num": per_page,
                        "page": page
                    },
                    timeout=15
                )

                if resp.status_code != 200:
                    break

                data = resp.json()
                organic = data.get("organic", [])

                if not organic:
                    break

                for item in organic:
                    url = item.get("link", "")
                    if not url or url in seen_urls:
                        continue

                    seen_urls.add(url)
                    parsed = urlparse(url)
                    domain = parsed.netloc

                    all_results.append({
                        "url": url,
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "domain": domain,
                    })

                page += 1

            except Exception as e:
                print(f"[ERR] 검색 오류: {e}")
                break

        return all_results[:num_results]

    def site_search(self, domain: str, num_results: int = 100) -> list[dict]:
        """site: 검색으로 해당 도메인의 페이지 수집"""
        all_results = []
        seen_urls = set()
        page = 1
        per_page = 10

        while len(all_results) < num_results and page <= 10:
            try:
                resp = self.session.post(
                    self.SERPER_URL,
                    json={
                        "q": f"site:{domain}",
                        "gl": "kr",
                        "hl": "ko",
                        "num": per_page,
                        "page": page
                    },
                    timeout=15
                )
                if resp.status_code != 200:
                    break

                data = resp.json()
                organic = data.get("organic", [])
                if not organic:
                    break

                for item in organic:
                    url = item.get("link", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append({
                            "url": url,
                            "title": item.get("title", ""),
                            "snippet": item.get("snippet", ""),
                            "domain": urlparse(url).netloc,
                        })

                page += 1
            except:
                break

        return all_results[:num_results]

    def search_domain(
        self,
        domain: str,
        brand_name: str = None,
        num_results: int = 100
    ) -> list[dict]:
        """
        도메인의 SEO 중요 페이지 수집

        Args:
            domain: 검색할 도메인 (예: "mtgal.com")
            brand_name: 브랜드명 (없으면 자동 추출)
            num_results: 최대 결과 수

        Returns:
            검색 결과 목록
        """
        # 1. 브랜드명 결정
        if not brand_name:
            brand_name = self.get_site_title(domain)
        if not brand_name:
            brand_name = self.extract_brand_name(domain)

        print(f"[INFO] 도메인: {domain}, 브랜드명: {brand_name}")

        all_results = []
        seen_urls = set()
        seen_categories = set()

        # 2. 브랜드명으로 검색 (타겟 도메인만)
        results = self.search_brand(brand_name, num_results)
        for item in results:
            if domain in item["domain"] and item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                all_results.append(item)

        # 3. site: 검색으로 페이지 수집
        results = self.site_search(domain, num_results)
        for item in results:
            url = item["url"]
            if url not in seen_urls:
                seen_urls.add(url)
                all_results.append(item)

            # 4. 게시글 URL에서 카테고리 추출
            path = urlparse(url).path.rstrip("/")
            segments = [s for s in path.split("/") if s]
            if len(segments) >= 2 and re.search(r'^\d+$', segments[-1]):
                # /category/123 형태 → /category 추출
                category = "/" + segments[0]
                if category not in seen_categories:
                    seen_categories.add(category)
                    category_url = f"https://{domain}{category}"
                    if category_url not in seen_urls:
                        seen_urls.add(category_url)
                        all_results.append({
                            "url": category_url,
                            "title": f"{segments[0]} 게시판",
                            "snippet": "",
                            "domain": domain,
                        })

        return all_results[:num_results]


def calculate_seo_score(url: str, title: str, snippet: str) -> int:
    """SEO 페이지 점수 계산 (짧은 경로 우선)"""
    parsed = urlparse(url)
    path = unquote(parsed.path).rstrip("/")
    query = parsed.query
    segments = [s for s in path.split("/") if s and not s.endswith(".php")]

    score = 0

    # 1. 경로 길이 기반 점수 (짧을수록 SEO 중요)
    if len(segments) == 0:  # 메인 페이지
        score += 100
    elif len(segments) == 1:  # 카테고리 페이지
        score += 80
    elif len(segments) == 2 and not re.search(r'/\d+$', path):  # 서브카테고리
        score += 60
    else:  # 개별 게시글
        score += 10

    # 2. 숫자 ID로 끝나면 개별 게시글 (감점)
    if re.search(r'/\d+/?$', path):
        score -= 50

    # 3. 긴 슬러그 = 게시글 (감점)
    for seg in segments:
        # 하이픈이 2개 이상 + 한글 포함 → 슬러그화된 제목
        if seg.count("-") >= 2 and re.search(r'[가-힣]', seg):
            score -= 80
        # 하이픈이 3개 이상 → 슬러그화된 제목
        elif seg.count("-") >= 3:
            score -= 80
        # 세그먼트가 20자 이상 → 게시글 제목
        if len(seg) > 20:
            score -= 70

    # 4. 금액 패턴 (만원, 천원) → 게시글
    if re.search(r'\d+만원|\d+천원', path):
        score -= 100

    # 5. 먹튀 신고글 패턴: "XXX-먹튀-XXX" 형태
    if re.search(r'-먹튀-.*com', path, re.IGNORECASE):
        score -= 100

    # 6. 쿼리 파라미터 감점
    if query:
        # 페이지네이션
        if re.search(r'page=\d+', query):
            score -= 50
        # 필터/검색 파라미터
        if re.search(r'sfl=|sst=|sod=|sca=', query):
            score -= 60
        # wr_id = 게시글 ID
        if 'wr_id=' in query:
            score -= 80

    # 7. 중요 키워드 보너스 (카테고리 페이지용)
    text = f"{path} {title}".lower()
    important_keywords = [
        "링크모음", "자유게시판", "후기게시판", "이벤트게시판",
        "login", "main", "show", "link"
    ]
    for kw in important_keywords:
        if kw in text:
            score += 15

    # 8. 시스템 페이지 감점
    system_keywords = ["register", "password", "logout", "captcha", "qalist"]
    for kw in system_keywords:
        if kw in path.lower():
            score -= 100

    return score


def filter_brand_results(
    results: list[dict],
    target_domain: str = None,
    min_score: int = 0,
    max_results: int = 100
) -> list[dict]:
    """
    브랜드 검색 결과 필터링 (SEO 페이지 우선)

    Args:
        results: 검색 결과
        target_domain: 타겟 도메인 (있으면 해당 도메인 우선)
        min_score: 최소 점수
        max_results: 최대 결과 수
    """
    scored = []
    for item in results:
        url = item.get("url", "")
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        domain = item.get("domain", "")

        score = calculate_seo_score(url, title, snippet)

        # 타겟 도메인이면 보너스
        if target_domain and target_domain in domain:
            score += 50

        if score >= min_score:
            scored.append({**item, "_score": score})

    # 점수순 정렬
    scored.sort(key=lambda x: x["_score"], reverse=True)

    # 중복 제거 (같은 경로 패턴)
    seen_patterns = set()
    unique = []
    for item in scored:
        path = urlparse(item["url"]).path.rstrip("/")
        # 숫자를 패턴으로 치환
        pattern = re.sub(r'/\d+', '/{id}', path)
        if pattern not in seen_patterns:
            seen_patterns.add(pattern)
            unique.append(item)

    # _score 제거하고 반환
    return [{k: v for k, v in item.items() if k != "_score"} for item in unique[:max_results]]


if __name__ == "__main__":
    import os

    api_key = os.environ.get("SERPER_API_KEY")
    if not api_key:
        config_path = os.path.expanduser("~/.url-collector")
        if os.path.exists(config_path):
            with open(config_path) as f:
                api_key = f.read().strip()

    if not api_key:
        print("API 키가 필요합니다")
        exit(1)

    searcher = BrandSearcher(api_key)

    # 테스트: mtgal.com
    print("=== mtgal.com 브랜드 검색 ===")
    results = searcher.search_domain("mtgal.com", num_results=20)

    print(f"\n총 {len(results)}개 결과:")
    for i, item in enumerate(results[:15], 1):
        print(f"{i:2d}. [{item['domain'][:20]:20s}] {item['title'][:40]}")
        print(f"    {item['url'][:70]}")
