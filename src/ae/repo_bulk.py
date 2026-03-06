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

_bulk_adapter = TypeAdapter(BulkOp)

def insert_bulk_op(db_path: str, op: BulkOp) -> None:
    con = db.connect(db_path)
    try:
        con.execute(
            """INSERT INTO bulk_ops(bulk_id, created_at, updated_at, mode, action, selector_json, status, result_json, notes)
                 VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                op.bulk_id,
                op.created_at.isoformat(),
                op.updated_at.isoformat(),
                op.mode,
                op.action,
                json.dumps(op.selector_json),
                op.status,
                json.dumps(op.result_json),
                op.notes,
            ),
        )
        con.commit()
    finally:
        con.close()

def try_claim_bulk_op(db_path: str, bulk_id: str) -> bool:
    """Atomically transition queued -> running. Returns True if claimed."""
    con = db.connect(db_path)
    try:
        con.isolation_level = None
        con.execute("BEGIN IMMEDIATE")
        row = db.fetchone(con, "SELECT status FROM bulk_ops WHERE bulk_id=?", (bulk_id,))
        if not row:
            con.execute("ROLLBACK")
            return False
        if row["status"] != "queued":
            con.execute("ROLLBACK")
            return False
        con.execute(
            "UPDATE bulk_ops SET status=?, updated_at=? WHERE bulk_id=?",
            ("running", datetime.utcnow().isoformat(), bulk_id),
        )
        con.execute("COMMIT")
        return True
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        con.close()

def update_bulk_op(db_path: str, bulk_id: str, status: str, result_json: dict) -> None:
    con = db.connect(db_path)
    try:
        con.execute(
            """UPDATE bulk_ops SET status=?, updated_at=?, result_json=? WHERE bulk_id=?""",
            (status, datetime.utcnow().isoformat(), json.dumps(result_json), bulk_id),
        )
        con.commit()
    finally:
        con.close()

def get_bulk_op(db_path: str, bulk_id: str) -> Optional[BulkOp]:
    con = db.connect(db_path)
    try:
        row = db.fetchone(con, "SELECT * FROM bulk_ops WHERE bulk_id=?", (bulk_id,))
        if not row:
            return None
        d = dict(row)
        d["created_at"] = _dt(d["created_at"])
        d["updated_at"] = _dt(d["updated_at"])
        d["selector_json"] = json.loads(d["selector_json"])
        d["result_json"] = json.loads(d["result_json"])
        return _bulk_adapter.validate_python(d)
    finally:
        con.close()

