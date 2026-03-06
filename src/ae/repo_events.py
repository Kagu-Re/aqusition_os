from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import TypeAdapter

from . import db
from .models import (
    Client, Template, Page, WorkItem, PublishLog, ChangeLog, EventRecord, BulkOp, AdStat
)
from .enums import PageStatus, WorkStatus, PublishAction, LogResult

def _dt(v: str) -> datetime:
    return datetime.fromisoformat(v)

_event_adapter = TypeAdapter(EventRecord)

def insert_event(db_path: str, ev: EventRecord) -> None:
    con = db.connect(db_path)
    try:
        con.execute(
            """INSERT INTO events(event_id, timestamp, page_id, event_name, params_json)
                 VALUES(?,?,?,?,?)""",
            (ev.event_id, ev.timestamp.isoformat(), ev.page_id, ev.event_name.value, json.dumps(ev.params_json))
        )
        con.commit()
    finally:
        con.close()

def has_validated_events(db_path: str, page_id: str) -> bool:
    # For v1: treat existence of at least one of each canonical event as validation
    con = db.connect(db_path)
    try:
        rows = db.fetchall(con, "SELECT event_name, COUNT(*) as c FROM events WHERE page_id=? GROUP BY event_name", (page_id,))
        got = {r["event_name"] for r in rows}
        return {"call_click", "quote_submit", "thank_you_view"}.issubset(got)
    finally:
        con.close()

def list_events(
    db_path: str,
    page_id: str | None = None,
    client_id: str | None = None,
) -> List[EventRecord]:
    """List events. When client_id is set, filter via page join (events.page_id -> pages.client_id)."""
    con = db.connect(db_path)
    try:
        if client_id:
            rows = db.fetchall(
                con,
                """SELECT e.* FROM events e
                   INNER JOIN pages p ON e.page_id = p.page_id
                   WHERE p.client_id = ?
                   ORDER BY e.timestamp ASC""",
                (client_id,),
            )
        elif page_id:
            rows = db.fetchall(con, "SELECT * FROM events WHERE page_id=? ORDER BY timestamp ASC", (page_id,))
        else:
            rows = db.fetchall(con, "SELECT * FROM events ORDER BY timestamp ASC")
        out: List[EventRecord] = []
        for row in rows:
            d = dict(row)
            d["timestamp"] = _dt(d["timestamp"])
            d["params_json"] = json.loads(d["params_json"])
            out.append(_event_adapter.validate_python(d))
        return out
    finally:
        con.close()


_adstat_adapter = TypeAdapter(AdStat)

