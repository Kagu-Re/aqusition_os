"""Minimal smoke checks for deployment validation.

Usage:
  python ops/checks/smoke.py --base-url http://127.0.0.1:8000 --db ./acq.db --secret YOURSECRET
"""

from __future__ import annotations
import argparse
import json
import sys
import urllib.request
import urllib.error

def _req(url: str, *, method: str = "GET", headers: dict | None = None, body: bytes | None = None) -> tuple[int, str]:
    req = urllib.request.Request(url, data=body, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--db", default=None)
    ap.add_argument("--secret", default=None)
    args = ap.parse_args()

    base = args.base_url.rstrip("/")
    db_q = f"?db={args.db}" if args.db else ""

    code, body = _req(f"{base}/healthz")
    if code != 200:
        print("FAIL /healthz", code, body)
        return 2

    code, body = _req(f"{base}/readyz{db_q}")
    if code != 200:
        print("FAIL /readyz", code, body)
        return 3

    # If secret provided, hit a protected endpoint to verify auth layer.
    if args.secret:
        code, body = _req(f"{base}/api/summary{db_q}", headers={"x-ae-secret": args.secret})
        if code != 200:
            print("FAIL /api/summary (auth?)", code, body)
            return 4

    print("OK smoke checks passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
