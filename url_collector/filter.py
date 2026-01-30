"""URL 필터링 - 게시글만 남기고 시스템/목록 페이지 제외 (범용 알고리즘)"""

import re
from urllib.parse import urlparse, parse_qs, unquote


# 시스템/리소스 경로 (절대 제외)
SYSTEM_PATHS = [
    # CMS 시스템 디렉토리
    r"/adm/", r"/admin/", r"/plugin/", r"/lib/", r"/extend/",
    r"/modules/", r"/widgets/", r"/addons/", r"/layouts/",
    r"/wp-admin", r"/wp-includes", r"/wp-content/", r"/wp-json",
    r"/files/attach", r"/files/cache", r"/data/file/",

    # 인증/세션
    r"/login", r"/logout", r"/signin", r"/signout", r"/signup",
    r"/register", r"/auth/", r"/oauth/", r"/password",

    # API/시스템
    r"/api/", r"/ajax/", r"/async/", r"/xmlrpc",
    r"/feed", r"/rss", r"/captcha", r"/robots\.txt", r"/favicon",
    r"/sitemap\.xml",
]

# 시스템 PHP 파일 (그누보드 등)
SYSTEM_PHP = [
    "login", "logout", "register", "password", "memo", "point",
    "scrap", "poll", "formmail", "qrcode", "new", "profile",
    "qalist", "link", "search", "tag", "shingo", "qa", "page",
]

# 정적 리소스 확장자
STATIC_EXTENSIONS = [
    r"\.xml$", r"\.json$", r"\.css$", r"\.js$",
    r"\.png$", r"\.jpg$", r"\.jpeg$", r"\.gif$", r"\.svg$", r"\.ico$",
    r"\.woff", r"\.ttf$", r"\.pdf$", r"\.zip$", r"\.rar$",
]

# 목록/검색 관련 파라미터
LIST_PARAMS = ["page", "sca", "sfl", "stx", "sop", "sst", "sod", "category", "cat"]
TRACKING_PARAMS = ["utm_", "fbclid", "gclid", "ref", "device"]


def _get_path_depth(path: str) -> int:
    """경로 깊이 계산 (유효한 세그먼트 수)"""
    segments = [s for s in path.split("/") if s and not s.endswith(".php")]
    return len(segments)


def _has_content_identifier(url: str) -> bool:
    """콘텐츠 식별자가 있는지 확인 (ID, 슬러그 등)"""
    parsed = urlparse(url)
    path = unquote(parsed.path).rstrip("/")
    query = parse_qs(parsed.query)

    # 1. 쿼리 파라미터로 게시글 ID 식별
    id_params = ["wr_id", "id", "no", "idx", "seq", "num", "article_id", "post_id", "document_srl"]
    for param in id_params:
        if param in query:
            return True

    # 2. 경로가 숫자 ID로 끝남: /board/123, /mt/5823
    if re.search(r"/\d+/?$", path):
        return True

    segments = [s for s in path.split("/") if s]
    if not segments:
        return False

    last_segment = segments[-1]

    # 3. 고유 ID 패턴 (해시, UUID, 랜덤 문자열)
    #    /community/review/8uev370xkibh7op, /post/abc123def
    if re.match(r"^[a-z0-9]{8,}$", last_segment, re.IGNORECASE):
        return True

    # 4. 슬러그 패턴 - 3단계 이상이거나, 확실한 슬러그일 때만
    #    /bsite/도미노-먹튀-dmn-vipcom/, /security/xxx-xxx/
    if len(segments) >= 2:
        # 하이픈이 2개 이상 = 제목 슬러그 (단어 구분)
        if last_segment.count("-") >= 2:
            return True

        # 한글 포함 + 하이픈 = 한글 제목 슬러그
        if re.search(r"[\uac00-\ud7af]", last_segment) and "-" in last_segment:
            return True

        # 3단계 이상 + 긴 마지막 세그먼트 = 게시글
        if len(segments) >= 3 and len(last_segment) > 10:
            return True

    return False


def _is_system_url(url: str) -> bool:
    """시스템/리소스 URL인지 확인"""
    parsed = urlparse(url)
    path = parsed.path.lower()

    # 1. 시스템 경로 패턴
    for pattern in SYSTEM_PATHS:
        if re.search(pattern, path, re.IGNORECASE):
            return True

    # 2. 정적 리소스 확장자
    for pattern in STATIC_EXTENSIONS:
        if re.search(pattern, path, re.IGNORECASE):
            return True

    # 3. 그누보드 시스템 PHP
    if "/bbs/" in path:
        for php in SYSTEM_PHP:
            if f"/{php}.php" in path or f"/{php}/" in path:
                return True

    return False


def _is_list_page(url: str) -> bool:
    """목록/카테고리 페이지인지 확인"""
    parsed = urlparse(url)
    path = unquote(parsed.path).rstrip("/")
    query = parse_qs(parsed.query)

    # 0. 콘텐츠 ID가 있으면 목록이 아님 (우선 체크)
    if _has_content_identifier(url):
        return False

    # 1. 루트/인덱스 페이지
    if path in ["", "/index.php", "/index.html", "/show.php", "/main"]:
        return True

    # 2. board.php 목록 (wr_id 없음)
    if "board.php" in path.lower() and "wr_id" not in query:
        return True

    segments = [s for s in path.split("/") if s and not s.endswith(".php")]
    depth = len(segments)

    # 3. 1단계 경로 = 카테고리/섹션
    if depth == 1:
        return True

    # 4. 카테고리/목록 패턴
    if segments:
        last = segments[-1]

        # "posts", "list", "page" 등으로 끝나는 경로 = 목록
        list_endings = ["posts", "list", "page", "items", "all", "archive"]
        if last.lower() in list_endings:
            return True

        # 2단계 경로의 카테고리 패턴
        if depth == 2:
            # 언더스코어 포함 카테고리명: community_xxx, post_xxx
            if "_" in last and not re.search(r"\d{3,}", last):
                return True
            # 짧은 한글 세그먼트 (카테고리명)
            if re.search(r"^[\uac00-\ud7af]+$", last) and len(last) <= 10:
                return True
            # 고유 ID 없는 짧은 영문 세그먼트
            if re.match(r"^[a-z_]+$", last, re.IGNORECASE) and len(last) <= 20:
                return True

    # 5. 목록/검색 파라미터만 있는 경우
    if query:
        query_keys = set(k.lower() for k in query.keys())
        list_keys = set(LIST_PARAMS) | set(TRACKING_PARAMS)
        if query_keys and query_keys.issubset(list_keys):
            return True

    return False


def is_article_url(url: str) -> bool:
    """게시글/콘텐츠 URL인지 확인 (범용)"""
    # 시스템 URL 제외
    if _is_system_url(url):
        return False

    # 목록 페이지 제외
    if _is_list_page(url):
        return False

    # 콘텐츠 식별자 확인
    return _has_content_identifier(url)


def is_list_or_main_page(url: str) -> bool:
    """목록/메인 페이지인지 확인 (호환성)"""
    return _is_list_page(url)


def filter_urls(urls: list[dict], strict: bool = False, max_per_domain: int = 50) -> list[dict]:
    """
    URL 필터링 - 게시글/콘텐츠만 남김 (범용 알고리즘)

    Args:
        urls: [{"url": ..., "title": ..., "snippet": ...}, ...]
        strict: True면 반드시 콘텐츠 식별자가 있어야 함
        max_per_domain: 도메인당 최대 URL 수 (기본 50)
    """
    from collections import defaultdict

    filtered = []
    seen = set()
    domain_counts = defaultdict(int)

    # 1단계: URL 구조 분석 (비슷한 구조가 많으면 게시글 패턴)
    structure_counts = defaultdict(int)
    for item in urls:
        url = item.get("url", "")
        if url:
            structure = _get_url_structure(url)
            structure_counts[structure] += 1

    for item in urls:
        url = item.get("url", "")
        if not url:
            continue

        # URL 정규화
        url = url.split("#")[0]

        # 중복 체크
        normalized = _normalize_url(url)
        if normalized in seen:
            continue
        seen.add(normalized)

        parsed = urlparse(url)
        domain = parsed.netloc

        # 도메인당 개수 제한
        if domain_counts[domain] >= max_per_domain:
            continue

        # 1. 시스템 URL 제외
        if _is_system_url(url):
            continue

        # 2. 게시글 판단
        is_article = False

        # 2a. wr_id 있으면 게시글
        query = parse_qs(parsed.query)
        if "wr_id" in query:
            is_article = True

        # 2b. 비슷한 구조 URL이 3개 이상이면 게시글 패턴
        if not is_article:
            structure = _get_url_structure(url)
            if structure_counts[structure] >= 3:
                is_article = True

        # 2c. 콘텐츠 식별자 있으면 게시글
        if not is_article and _has_content_identifier(url):
            is_article = True

        # 3. 목록 페이지는 제외 (단, 위에서 게시글로 판단되면 유지)
        if not is_article and _is_list_page(url):
            continue

        # 4. strict 모드
        if strict and not is_article:
            continue

        filtered.append({
            "url": url,
            "title": item.get("title", ""),
            "snippet": item.get("snippet", "")
        })
        domain_counts[domain] += 1

    return filtered


def _get_url_structure(url: str) -> str:
    """URL 구조 패턴 추출 (비슷한 URL 그룹화용)"""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")

    # 경로에서 숫자/ID를 플레이스홀더로 변환
    # /bbs/board.php -> /bbs/board.php
    # /free/12345 -> /free/{id}
    # /post/some-slug -> /post/{slug}
    segments = path.split("/")
    normalized = []
    for seg in segments:
        if not seg:
            continue
        if seg.endswith(".php"):
            normalized.append(seg)
        elif re.match(r"^\d+$", seg):
            normalized.append("{id}")
        elif len(seg) > 10 and ("-" in seg or re.search(r"[\uac00-\ud7af]", seg)):
            normalized.append("{slug}")
        elif re.match(r"^[a-z0-9]{8,}$", seg, re.IGNORECASE):
            normalized.append("{hash}")
        else:
            normalized.append(seg)

    # 쿼리 파라미터 키만 추출
    query_keys = sorted(parse_qs(parsed.query).keys())
    query_pattern = "&".join(query_keys) if query_keys else ""

    return f"{parsed.netloc}/{'/'.join(normalized)}?{query_pattern}"


def _normalize_url(url: str) -> str:
    """URL 정규화 (중복 제거용)"""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    # 트래킹 파라미터 제거
    clean_query = {k: v for k, v in query.items()
                   if not any(k.lower().startswith(t) for t in TRACKING_PARAMS)}

    # 쿼리 재구성
    if clean_query:
        sorted_query = "&".join(f"{k}={v[0]}" for k, v in sorted(clean_query.items()))
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{sorted_query}"

    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
