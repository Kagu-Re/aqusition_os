from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import List, Optional

from pydantic import TypeAdapter

from . import db
from .models import HookRetry


def _dt(v: str) -> datetime:
    return datetime.fromisoformat(v)


_retry_adapter = TypeAdapter(HookRetry)


def enqueue_hook_retry(
    db_path: str,
    *,
    event_id: str,
    hook_name: str,
    topic: str,
    error: str,
    max_attempts: int = 6,
    delay_seconds: int = 60,
) -> HookRetry:
    """Insert (or update) a retry record for a failed hook delivery.

    - Idempotent per (event_id, hook_name) while status is pending.
    - Increments attempt and schedules next_attempt_at.
    """
    now = datetime.utcnow()
    con = db.connect(db_path)
    try:
        row = con.execute(
            """SELECT retry_id, attempt, max_attempts, status
                 FROM hook_retries
                 WHERE event_id=? AND hook_name=?
                 ORDER BY created_at DESC
                 LIMIT 1""",
            (event_id, hook_name),
        ).fetchone()

        if row and row[3] == "pending":
            retry_id, attempt, max_attempts_existing, _status = row
            attempt_next = int(attempt) + 1
            max_attempts_use = int(max_attempts_existing)
            next_at = now + timedelta(seconds=int(delay_seconds) * (2 ** (attempt_next - 1)))
            con.execute(
                """UPDATE hook_retries
                     SET attempt=?, next_attempt_at=?, last_error=?, updated_at=?
                     WHERE retry_id=?""",
                (
                    attempt_next,
                    next_at.isoformat(),
                    error[:2000],
                    now.isoformat(),
                    retry_id,
                ),
            )
        else:
            retry_id = f"hr_{event_id[:8]}_{hook_name}_{now.strftime('%Y%m%d%H%M%S%f')}"
            attempt_next = 1
            max_attempts_use = max_attempts
            next_at = now + timedelta(seconds=int(delay_seconds) * (2 ** (attempt_next - 1)))
            con.execute(
                """INSERT INTO hook_retries(
                        retry_id, event_id, hook_name, topic,
                        attempt, max_attempts, status,
                        next_attempt_at, last_error,
                        created_at, updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    retry_id,
                    event_id,
                    hook_name,
                    topic,
                    attempt_next,
                    max_attempts_use,
                    "pending",
                    next_at.isoformat(),
                    error[:2000],
                    now.isoformat(),
                    now.isoformat(),
                ),
            )

        con.commit()

        out = con.execute(
            """SELECT retry_id, event_id, hook_name, topic, attempt, max_attempts, status,
                      next_attempt_at, last_error, created_at, updated_at
                 FROM hook_retries WHERE retry_id=?""",
            (retry_id,),
        ).fetchone()
        return _retry_adapter.validate_python(
            {
                "retry_id": out[0],
                "event_id": out[1],
                "hook_name": out[2],
                "topic": out[3],
                "attempt": out[4],
                "max_attempts": out[5],
                "status": out[6],
                "next_attempt_at": _dt(out[7]),
                "last_error": out[8],
                "created_at": _dt(out[9]),
                "updated_at": _dt(out[10]),
            }
        )
    finally:
        con.close()


def list_due_hook_retries(
    db_path: str,
    *,
    now: Optional[datetime] = None,
    limit: int = 50,
) -> List[HookRetry]:
    now = now or datetime.utcnow()
    con = db.connect(db_path)
    try:
        rows = con.execute(
            """SELECT retry_id, event_id, hook_name, topic, attempt, max_attempts, status,
                      next_attempt_at, last_error, created_at, updated_at
                 FROM hook_retries
                 WHERE status='pending' AND next_attempt_at <= ?
                 ORDER BY next_attempt_at ASC
                 LIMIT ?""",
            (now.isoformat(), int(limit)),
        ).fetchall()
        return [
            _retry_adapter.validate_python(
                {
                    "retry_id": r[0],
                    "event_id": r[1],
                    "hook_name": r[2],
                    "topic": r[3],
                    "attempt": r[4],
                    "max_attempts": r[5],
                    "status": r[6],
                    "next_attempt_at": _dt(r[7]),
                    "last_error": r[8],
                    "created_at": _dt(r[9]),
                    "updated_at": _dt(r[10]),
                }
            )
            for r in rows
        ]
    finally:
        con.close()


def get_hook_retry(db_path: str, retry_id: str) -> Optional[HookRetry]:
    con = db.connect(db_path)
    try:
        r = con.execute(
            """SELECT retry_id, event_id, hook_name, topic, attempt, max_attempts, status,
                      next_attempt_at, last_error, created_at, updated_at
                 FROM hook_retries WHERE retry_id=?""",
            (retry_id,),
        ).fetchone()
        if not r:
            return None
        return _retry_adapter.validate_python(
            {
                "retry_id": r[0],
                "event_id": r[1],
                "hook_name": r[2],
                "topic": r[3],
                "attempt": r[4],
                "max_attempts": r[5],
                "status": r[6],
                "next_attempt_at": _dt(r[7]),
                "last_error": r[8],
                "created_at": _dt(r[9]),
                "updated_at": _dt(r[10]),
            }
        )
    finally:
        con.close()


def mark_hook_retry(
    db_path: str,
    retry_id: str,
    *,
    status: str,
    error: Optional[str] = None,
    next_attempt_at: Optional[datetime] = None,
) -> None:
    now = datetime.utcnow()
    con = db.connect(db_path)
    try:
        con.execute(
            """UPDATE hook_retries
                 SET status=?, last_error=?, next_attempt_at=?, updated_at=?
                 WHERE retry_id=?""",
            (
                status,
                (error[:2000] if error else None),
                (next_attempt_at.isoformat() if next_attempt_at else now.isoformat()),
                now.isoformat(),
                retry_id,
            ),
        )
        con.commit()
    finally:
        con.close()


def list_hook_retries(
    db_path: str,
    *,
    status: Optional[str] = None,
    limit: int = 100,
) -> List[HookRetry]:
    con = db.connect(db_path)
    try:
        if status:
            rows = con.execute(
                """SELECT retry_id, event_id, hook_name, topic, attempt, max_attempts, status,
                          next_attempt_at, last_error, created_at, updated_at
                     FROM hook_retries
                     WHERE status=?
                     ORDER BY updated_at DESC
                     LIMIT ?""",
                (status, int(limit)),
            ).fetchall()
        else:
            rows = con.execute(
                """SELECT retry_id, event_id, hook_name, topic, attempt, max_attempts, status,
                          next_attempt_at, last_error, created_at, updated_at
                     FROM hook_retries
                     ORDER BY updated_at DESC
                     LIMIT ?""",
                (int(limit),),
            ).fetchall()
        return [
            _retry_adapter.validate_python(
                {
                    "retry_id": r[0],
                    "event_id": r[1],
                    "hook_name": r[2],
                    "topic": r[3],
                    "attempt": r[4],
                    "max_attempts": r[5],
                    "status": r[6],
                    "next_attempt_at": _dt(r[7]),
                    "last_error": r[8],
                    "created_at": _dt(r[9]),
                    "updated_at": _dt(r[10]),
                }
            )
            for r in rows
        ]
    finally:
        con.close()
