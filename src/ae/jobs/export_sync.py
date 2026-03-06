from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

from ..export_sync_runner import run_due_export_jobs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run scheduled export sync jobs.")
    parser.add_argument("--db", required=True, help="Path to sqlite db")
    parser.add_argument("--run-once", action="store_true", help="Run due jobs once and exit")
    parser.add_argument("--sleep", type=int, default=60, help="Worker sleep seconds between polls")
    parser.add_argument("--limit", type=int, default=50, help="Max due jobs per tick")
    parser.add_argument("--json", action="store_true", help="Print JSON results")
    args = parser.parse_args()

    def tick() -> None:
        res = run_due_export_jobs(args.db, now=datetime.now(timezone.utc), limit=args.limit)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"[{res['now']}] ran {res['count']} job(s)")
            for r in res["results"]:
                if r["status"] == "ok":
                    print(f"- ok {r['job_id']} preset={r['preset_name']} rows={r['row_count']} out={r['output_path']}")
                else:
                    print(f"- err {r['job_id']} preset={r['preset_name']} error={r['error']}")

    if args.run_once:
        tick()
        return

    while True:
        tick()
        time.sleep(max(1, args.sleep))


if __name__ == "__main__":
    main()
