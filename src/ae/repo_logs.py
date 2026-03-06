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

_publog_adapter = TypeAdapter(PublishLog)
_changelog_adapter = TypeAdapter(ChangeLog)

def insert_publish_log(db_path: str, log: PublishLog) -> None:
    con = db.connect(db_path)
    try:
        con.execute(
            """INSERT INTO publish_logs(log_id, timestamp, client_id, page_id, template_id, template_version,
                                          content_version, action, result, notes)
                 VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                log.log_id, log.timestamp.isoformat(), log.client_id, log.page_id, log.template_id,
                log.template_version, log.content_version, log.action.value, log.result.value, log.notes
            )
        )
        con.commit()
    finally:
        con.close()

def insert_change_log(db_path: str, log: ChangeLog) -> None:
    con = db.connect(db_path)
    try:
        con.execute(
            """INSERT INTO change_logs(log_id, timestamp, client_id, page_id, content_version_before, content_version_after,
                                          changed_fields_json, notes)
                 VALUES(?,?,?,?,?,?,?,?)""",
            (
                log.log_id, log.timestamp.isoformat(), log.client_id, log.page_id,
                log.content_version_before, log.content_version_after, json.dumps(log.changed_fields), log.notes
            )
        )
        con.commit()
    finally:
        con.close()

def get_last_successful_publish_log(db_path: str, page_id: str) -> Optional[PublishLog]:
    con = db.connect(db_path)
    try:
        row = db.fetchone(
            con,
            "SELECT * FROM publish_logs WHERE page_id=? AND action=? AND result=? ORDER BY timestamp DESC LIMIT 1",
            (page_id, "publish", "success"),
        )
        if not row:
            return None
        d = dict(row)
        d["timestamp"] = _dt(d["timestamp"])
        return _publog_adapter.validate_python(d)
    finally:
        con.close()

