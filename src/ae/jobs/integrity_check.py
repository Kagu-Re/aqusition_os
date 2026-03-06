from __future__ import annotations

import argparse
import json
from ..integrity_validator import run_integrity_check


def main() -> None:
    parser = argparse.ArgumentParser(description="Run integrity validator against a DB.")
    parser.add_argument("--db", required=True, help="Path to sqlite db")
    parser.add_argument("--no-events", action="store_true", help="Do not emit op.rel.integrity.* events")
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    args = parser.parse_args()

    report = run_integrity_check(args.db, emit_events=not args.no_events)
    if args.json:
        print(json.dumps(report.model_dump(), indent=2))
    else:
        print(f"Integrity report {report.report_id} status={report.status} issues={len(report.issues)}")
        for issue in report.issues[:50]:
            print(f"- [{issue.severity}] {issue.code}: {issue.message}")


if __name__ == "__main__":
    main()
