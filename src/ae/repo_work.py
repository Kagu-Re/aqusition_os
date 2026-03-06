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

_work_adapter = TypeAdapter(WorkItem)

def upsert_work_item(db_path: str, item: WorkItem) -> None:
    con = db.connect(db_path)
    try:
        con.execute(
            """INSERT INTO work_items(work_item_id, type, client_id, page_id, status, priority, owner,
                                         acceptance_criteria, blocker_reason, links_json, created_at, updated_at)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                 ON CONFLICT(work_item_id) DO UPDATE SET
                    type=excluded.type,
                    client_id=excluded.client_id,
                    page_id=excluded.page_id,
                    status=excluded.status,
                    priority=excluded.priority,
                    owner=excluded.owner,
                    acceptance_criteria=excluded.acceptance_criteria,
                    blocker_reason=excluded.blocker_reason,
                    links_json=excluded.links_json,
                    updated_at=excluded.updated_at
            """,
            (
                item.work_item_id, item.type.value, item.client_id, item.page_id,
                item.status.value, item.priority.value, item.owner,
                item.acceptance_criteria, item.blocker_reason,
                json.dumps(item.links_json),
                item.created_at.isoformat(), item.updated_at.isoformat()
            )
        )
        con.commit()
    finally:
        con.close()

def list_work(db_path: str, status: Optional[str] = None) -> List[WorkItem]:
    con = db.connect(db_path)
    try:
        if status:
            rows = db.fetchall(con, "SELECT * FROM work_items WHERE status=? ORDER BY created_at DESC", (status,))
        else:
            rows = db.fetchall(con, "SELECT * FROM work_items ORDER BY created_at DESC", ())
        items: List[WorkItem] = []
        for r in rows:
            d = dict(r)
            d["type"] = d["type"]
            d["status"] = d["status"]
            d["priority"] = d["priority"]
            d["links_json"] = json.loads(d["links_json"])
            d["created_at"] = _dt(d["created_at"])
            d["updated_at"] = _dt(d["updated_at"])
            items.append(_work_adapter.validate_python(d))
        return items
    finally:
        con.close()

