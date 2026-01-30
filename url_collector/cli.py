"""CLI - SERP API 기반"""

import argparse
import json
import os
import sys

from .serper import SerperClient
from .filter import filter_urls


def get_api_key() -> str | None:
    key = os.environ.get("SERPER_API_KEY")
    if key:
        return key
    config_path = os.path.expanduser("~/.url-collector")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return f.read().strip()
    return None


def save_api_key(key: str):
    config_path = os.path.expanduser("~/.url-collector")
    with open(config_path, "w") as f:
        f.write(key)
    print(f"[OK] API 키 저장됨: {config_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Google site: 검색 URL 수집기 (SERP API)",
        epilog="""
예제:
  python -m url_collector.cli mtgal.com
  python -m url_collector.cli site1.com site2.com
  python -m url_collector.cli mtgal.com -f json > urls.json
  python -m url_collector.cli --set-key YOUR_API_KEY

GUI:
  python -m url_collector.gui
        """
    )

    parser.add_argument("domains", nargs="*", help="도메인")
    parser.add_argument("-n", "--num", type=int, default=100, help="최대 결과 수")
    parser.add_argument("-f", "--format", choices=["table", "json", "txt"], default="table")
    parser.add_argument("-o", "--output", help="파일로 저장")
    parser.add_argument("--no-filter", action="store_true", help="필터링 비활성화")
    parser.add_argument("--set-key", metavar="KEY", help="API 키 저장")
    parser.add_argument("--gui", action="store_true", help="GUI 실행")

    args = parser.parse_args()

    if args.gui:
        from .gui import main as gui_main
        gui_main()
        return

    if args.set_key:
        save_api_key(args.set_key)
        return

    if not args.domains:
        parser.print_help()
        sys.exit(1)

    api_key = get_api_key()
    if not api_key:
        print("[ERR] API 키 필요. --set-key 또는 SERPER_API_KEY 환경변수 설정")
        sys.exit(1)

    client = SerperClient(api_key)
    results = {}

    for domain in args.domains:
        domain = domain.replace("https://", "").replace("http://", "").rstrip("/")
        print(f"[...] {domain}", end="", flush=True)

        try:
            raw = client.site_search(domain, num_results=args.num)
            filtered = raw if args.no_filter else filter_urls(raw, strict=False)
            results[domain] = filtered
            print(f"\r[OK] {domain}: {len(filtered)}개")
        except Exception as e:
            print(f"\r[ERR] {domain}: {e}")
            results[domain] = []

    # 출력
    if args.format == "json":
        out = {d: [u["url"] for u in urls] for d, urls in results.items()}
        print(json.dumps(out, indent=2, ensure_ascii=False))
    elif args.format == "txt":
        for domain, urls in results.items():
            print(f"\n# {domain}")
            for u in urls:
                print(u["url"])
    else:
        for domain, urls in results.items():
            print(f"\n=== {domain} ({len(urls)}개) ===")
            for u in urls:
                print(f"  {u['url']}")

    if args.output:
        lines = []
        for domain, urls in results.items():
            lines.append(f"# {domain}")
            lines.extend(u["url"] for u in urls)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"\n[OK] 저장됨: {args.output}")

    total = sum(len(u) for u in results.values())
    print(f"\n총 {total}개 URL")


if __name__ == "__main__":
    main()
