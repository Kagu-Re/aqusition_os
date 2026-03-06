from __future__ import annotations

import argparse
from datetime import datetime
from typing import Optional

from ..hooks import GLOBAL_HOOKS
from ..repo_hook_retries import list_due_hook_retries, mark_hook_retry, enqueue_hook_retry
from ..repo_op_events import get_op_event
from ..repo_activity import append_activity


def process_due(db_path: str, *, limit: int = 50) -> int:
    processed = 0
    due = list_due_hook_retries(db_path, limit=limit)
    for r in due:
        ev = get_op_event(db_path, r.event_id)
        if ev is None:
            mark_hook_retry(db_path, r.retry_id, status="dead", error="Missing op_event for retry")
            continue

        spec = GLOBAL_HOOKS.get_by_name(r.hook_name)
        if spec is None:
            mark_hook_retry(db_path, r.retry_id, status="dead", error="Missing hook implementation")
            continue

        try:
            spec.fn(db_path, ev)
            mark_hook_retry(db_path, r.retry_id, status="succeeded", error=None)
            processed += 1
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            # log activity (best-effort)
            try:
                append_activity(
                    db_path,
                    action="hook_retry_error",
                    entity_type="hook_retry",
                    entity_id=r.retry_id,
                    actor=ev.actor,
                    details={"hook": r.hook_name, "topic": r.topic, "error": err, "attempt": r.attempt},
                )
            except Exception:
                pass

            if r.attempt >= r.max_attempts:
                mark_hook_retry(db_path, r.retry_id, status="dead", error=err)
            else:
                # increment attempt + schedule next (exponential backoff)
                enqueue_hook_retry(
                    db_path,
                    event_id=r.event_id,
                    hook_name=r.hook_name,
                    topic=r.topic,
                    error=err,
                    max_attempts=r.max_attempts,
                    delay_seconds=60,
                )
    return processed


def main(argv: Optional[list[str]] = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--run-once", action="store_true")
    args = ap.parse_args(argv)

    # Simple runner: run once and exit
    processed = process_due(args.db, limit=args.limit)
    print(f"processed={processed}")


if __name__ == "__main__":
    main()
