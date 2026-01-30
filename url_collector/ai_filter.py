"""스마트 URL 필터링 - SEO 중요 페이지 우선 (빠르고 무료)"""

import re
from urllib.parse import urlparse, unquote, parse_qs


# SEO 중요 페이지 패턴 (높은 점수)
SEO_IMPORTANT = {
    # 메인/랜딩 페이지
    "메인": 20, "홈": 15, "소개": 15, "안내": 15,
    "main": 20, "home": 15, "about": 15, "intro": 15,

    # 주요 카테고리/게시판
    "먹튀검증": 25, "먹튀제보": 25, "먹튀신고": 25,
    "토토사이트": 20, "카지노사이트": 20, "안전놀이터": 20,
    "보증업체": 20, "검증업체": 20, "추천업체": 20,

    # 핵심 기능 페이지
    "verification": 25, "report": 20, "review": 15,
    "notice": 15, "event": 10, "faq": 10,
}

# 게시판 테이블 중요도 (bo_table 파라미터)
IMPORTANT_BOARDS = {
    "verification": 25, "mt_site": 25, "report": 20,
    "notice": 15, "event": 10, "info": 10,
    "review": 15, "qa": 10,
}

# 개별 게시글 패턴 (낮은 점수)
ARTICLE_PENALTY = -10  # 개별 게시글은 감점


def calculate_score(url: str, title: str, snippet: str) -> int:
    """URL의 SEO 중요도 점수 계산"""
    score = 0
    parsed = urlparse(url)
    path = unquote(parsed.path).lower().rstrip("/")
    query = parse_qs(parsed.query)
    text = f"{title} {snippet}".lower()

    # 1. 메인/랜딩 페이지 (최고 점수)
    if path in ["", "/", "/index.php", "/index.html", "/main"]:
        score += 30

    # 2. 1단계 카테고리 페이지 (navbar 링크)
    segments = [s for s in path.split("/") if s and not s.endswith(".php")]
    if len(segments) == 1:
        score += 20

    # 3. 게시판 목록 페이지 (SEO 핵심)
    if "board.php" in path and "bo_table" in query:
        bo_table = query.get("bo_table", [""])[0].lower()
        # wr_id 없음 = 목록 페이지 (중요)
        if "wr_id" not in query:
            score += 25
            # 특정 게시판 보너스
            for board, points in IMPORTANT_BOARDS.items():
                if board in bo_table:
                    score += points
                    break
        else:
            # wr_id 있음 = 개별 게시글 (덜 중요)
            score += ARTICLE_PENALTY

    # 4. 개별 게시글 패턴 감점
    # /mtcs/228, /mt/4446, /review/554 등
    if re.search(r"/\d+/?$", path):
        score += ARTICLE_PENALTY

    # 5. 제목/URL 키워드 점수
    for keyword, points in SEO_IMPORTANT.items():
        if keyword in text or keyword in path:
            score += points

    # 6. 시스템 페이지 감점
    system_pages = [
        "login", "logout", "register", "password", "member", "captcha",
        "current_connect", "new.php", "qalist", "profile", "memo",
        "point", "scrap", "formmail", "qrcode",
    ]
    for sys_page in system_pages:
        if sys_page in path:
            score -= 50
            break

    # 7. 필터/페이지네이션 파라미터 있으면 대폭 감점 (중복 페이지)
    filter_params = ["sca", "page", "sfl", "stx", "sop", "sst", "sod"]
    for param in filter_params:
        if param in query:
            score -= 80  # 중복 페이지는 거의 제외
            break

    # 8. 중요하지 않은 게시판 감점
    unimportant_boards = ["chulsuk", "attendance", "출석", "coupon", "쿠폰"]
    if "bo_table" in query:
        bo_table = query.get("bo_table", [""])[0].lower()
        for board in unimportant_boards:
            if board in bo_table:
                score -= 80  # 불필요한 게시판 제외
                break

    return score


def smart_filter_urls(
    urls: list[dict],
    min_score: int = 0,
    top_n: int = None,
    callback=None
) -> list[dict]:
    """
    스마트 필터링 - 점수 기반으로 중요한 URL만 선택

    Args:
        urls: [{"url": ..., "title": ..., "snippet": ...}, ...]
        min_score: 최소 점수 (이하는 제외)
        top_n: 상위 N개만 선택 (None이면 전체)
        callback: 진행 상황 콜백

    Returns:
        점수순 정렬된 URL 목록
    """
    scored = []
    total = len(urls)

    for i, item in enumerate(urls):
        if callback:
            callback(i + 1, total, item.get("url", ""))

        url = item.get("url", "")
        title = item.get("title", "")
        snippet = item.get("snippet", "")

        score = calculate_score(url, title, snippet)

        if score >= min_score:
            scored.append({
                **item,
                "_score": score
            })

    # 점수순 정렬
    scored.sort(key=lambda x: x["_score"], reverse=True)

    # 상위 N개 선택
    if top_n:
        scored = scored[:top_n]

    # _score 제거하고 반환
    return [{k: v for k, v in item.items() if k != "_score"} for item in scored]


def filter_by_category(urls: list[dict], include_categories: list[str] = None) -> list[dict]:
    """
    URL 경로의 카테고리로 필터링

    Args:
        urls: URL 목록
        include_categories: 포함할 카테고리 (None이면 전체)
            예: ["scamdb", "report_scammer", "validate", "verify"]
    """
    if not include_categories:
        return urls

    filtered = []
    for item in urls:
        path = unquote(urlparse(item.get("url", "")).path).lower()
        for cat in include_categories:
            if cat.lower() in path:
                filtered.append(item)
                break

    return filtered


if __name__ == "__main__":
    # 테스트 - SEO 중요 페이지 vs 개별 게시글
    test_urls = [
        # SEO 중요 페이지 (높은 점수)
        {"url": "https://mtcheck.net/", "title": "먹튀검증 - 메인", "snippet": ""},
        {"url": "https://mtcheck.net/kr1/bbs/board.php?bo_table=Verification", "title": "먹튀검증 게시판", "snippet": ""},
        {"url": "https://mtcheck.net/kr1/bbs/board.php?bo_table=mt_site", "title": "토토사이트 목록", "snippet": ""},
        {"url": "https://mtcheck.net/kr1/bbs/board.php?bo_table=report", "title": "먹튀신고 게시판", "snippet": ""},
        {"url": "https://example.com/토토사이트", "title": "토토사이트 추천", "snippet": ""},

        # 개별 게시글 (낮은 점수)
        {"url": "https://mtgal.com/mtcs/228", "title": "개별 게시글 1", "snippet": ""},
        {"url": "https://mtgal.com/mt/4446", "title": "개별 게시글 2", "snippet": ""},
        {"url": "https://example.com/bbs/board.php?bo_table=free&wr_id=123", "title": "자유게시판 글", "snippet": ""},

        # 시스템 페이지 (제외)
        {"url": "https://mtcheck.net/bbs/register.php", "title": "회원가입", "snippet": ""},
        {"url": "https://mtcheck.net/bbs/login.php", "title": "로그인", "snippet": ""},
    ]

    print("=== SEO 중요도 스코어링 테스트 ===")
    for item in test_urls:
        score = calculate_score(item["url"], item["title"], item["snippet"])
        print(f"[{score:4d}점] {item['url'][:50]}")

    print()
    print("=== 필터링 테스트 (상위 5개) ===")
    filtered = smart_filter_urls(test_urls, min_score=0, top_n=5)
    for item in filtered:
        score = calculate_score(item["url"], item["title"], item["snippet"])
        print(f"  [{score:3d}] {item['url'][:60]}")

