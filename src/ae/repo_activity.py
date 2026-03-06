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

_activity_adapter = TypeAdapter(dict)

def append_activity(
    db_path: str,
    *,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    actor: Optional[str] = None,
    details: Optional[dict] = None,
) -> int:
    from .db import connect, init_db
    import json as _json
    from datetime import datetime

    details_json = _json.dumps(details or {}, ensure_ascii=False)
    ts = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    with connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO activity_log (ts, actor, action, entity_type, entity_id, details_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ts, actor, action, entity_type, entity_id, details_json),
        )
        conn.commit()
        return int(cur.lastrowid)

def list_activity(
    db_path: str,
    *,
    limit: int = 200,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
):
    from .db import connect, init_db
    import json as _json
    from .models import Activity

    where = []
    params = []
    if action:
        where.append("action = ?")
        params.append(action)
    if entity_type:
        where.append("entity_type = ?")
        params.append(entity_type)
    if entity_id:
        where.append("entity_id = ?")
        params.append(entity_id)

    w = (" WHERE " + " AND ".join(where)) if where else ""
    sql = (
        "SELECT activity_id, ts, actor, action, entity_type, entity_id, details_json "
        "FROM activity_log"
        f"{w} ORDER BY activity_id DESC LIMIT ?"
    )
    params.append(int(limit))
    with connect(db_path) as conn:
        cur = conn.cursor()
        rows = cur.execute(sql, params).fetchall()

    items = []
    for r in rows:
        details = {}
        try:
            details = _json.loads(r[6] or "{}")
        except Exception:
            details = {}
        items.append(
            Activity(
                activity_id=r[0],
                ts=r[1],
                actor=r[2],
                action=r[3],
                entity_type=r[4],
                entity_id=r[5],
                details_json=details,
            )
        )
    return items

# --- Lead intake ---

