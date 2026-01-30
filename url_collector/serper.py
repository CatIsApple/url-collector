"""Serper.dev API를 이용한 Google site: 검색"""

import requests


class SerperClient:
    """Serper.dev API 클라이언트"""

    BASE_URL = "https://google.serper.dev/search"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
            "Accept-Encoding": "identity"  # 압축 해제 오류 방지
        })

    def site_search(
        self,
        domain: str,
        num_results: int = 100,
        country: str = "kr",
        language: str = "ko"
    ) -> list[dict]:
        """Google site: 검색"""
        domain = domain.replace("https://", "").replace("http://", "").rstrip("/")

        all_results = []
        seen_urls = set()
        page = 1
        per_page = 10  # Serper 무료 플랜 제한
        max_pages = (num_results + per_page - 1) // per_page  # 필요한 최소 페이지 수

        while len(all_results) < num_results and page <= max_pages:
            payload = {
                "q": f"site:{domain}",
                "gl": country,
                "hl": language,
                "num": per_page,
                "page": page
            }

            try:
                response = self.session.post(self.BASE_URL, json=payload)
                response.raise_for_status()
                data = response.json()

                organic = data.get("organic", [])
                if not organic:
                    break

                new_count = 0
                for item in organic:
                    url = item.get("link", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append({
                            "url": url,
                            "title": item.get("title", ""),
                            "snippet": item.get("snippet", "")
                        })
                        new_count += 1

                if new_count == 0:
                    break

                page += 1

            except requests.RequestException as e:
                raise Exception(f"Serper API 요청 실패: {e}")

        return all_results[:num_results]
