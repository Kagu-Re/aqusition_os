from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple

from .db import connect, init_db


def get_state(db_path: str, *, aggregate_type: str, aggregate_id: str) -> Optional[str]:
    """Return the current materialized state for an aggregate, or None if unknown."""
    init_db(db_path)
    with connect(db_path) as conn:
        cur = conn.cursor()
        row = cur.execute(
            "SELECT state FROM op_states WHERE aggregate_type = ? AND aggregate_id = ?",
            (aggregate_type, aggregate_id),
        ).fetchone()
        if not row:
            return None
        return str(row[0])


def get_state_row(
    db_path: str, *, aggregate_type: str, aggregate_id: str
) -> Optional[Tuple[str, str, Optional[str], Optional[str], Optional[str]]]:
    """Return (state, updated_at, last_event_id, last_topic, last_occurred_at) or None."""
    init_db(db_path)
    with connect(db_path) as conn:
        cur = conn.cursor()
        row = cur.execute(
            """SELECT state, updated_at, last_event_id, last_topic, last_occurred_at
               FROM op_states WHERE aggregate_type = ? AND aggregate_id = ?""",
            (aggregate_type, aggregate_id),
        ).fetchone()
        if not row:
            return None
        return (str(row[0]), str(row[1]), row[2], row[3], row[4])


def upsert_state(
    db_path: str,
    *,
    aggregate_type: str,
    aggregate_id: str,
    state: str,
    updated_at: datetime,
    last_event_id: Optional[str] = None,
    last_topic: Optional[str] = None,
    last_occurred_at: Optional[datetime] = None,
) -> None:
    """Upsert current state for an aggregate."""
    init_db(db_path)
    updated_at_str = updated_at.replace(microsecond=0).isoformat() + "Z"
    last_occurred_at_str = (
        last_occurred_at.replace(microsecond=0).isoformat() + "Z" if last_occurred_at else None
    )
    with connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO op_states(
                   aggregate_type, aggregate_id, state, updated_at, last_event_id, last_topic, last_occurred_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(aggregate_type, aggregate_id) DO UPDATE SET
                   state=excluded.state,
                   updated_at=excluded.updated_at,
                   last_event_id=excluded.last_event_id,
                   last_topic=excluded.last_topic,
                   last_occurred_at=excluded.last_occurred_at
            """,
            (
                aggregate_type,
                aggregate_id,
                state,
                updated_at_str,
                last_event_id,
                last_topic,
                last_occurred_at_str,
            ),
        )
        conn.commit()
