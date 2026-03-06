import argparse
import json
import urllib.parse

import requests


def main() -> int:
    ap = argparse.ArgumentParser(description="Acquisition Engine: query top rate-limited offenders from Operator Console")
    ap.add_argument("--base-url", required=True, help="Console base URL (e.g., http://localhost:8001)")
    ap.add_argument("--secret", required=True, help="Operator console secret")
    ap.add_argument("--limit", type=int, default=20, help="Max items")
    args = ap.parse_args()

    url = args.base_url.rstrip("/") + "/api/abuse/top?" + urllib.parse.urlencode({"limit": args.limit})
    r = requests.get(url, headers={"X-AE-SECRET": args.secret}, timeout=10)
    r.raise_for_status()
    print(json.dumps(r.json(), indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
