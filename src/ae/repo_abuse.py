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

def insert_abuse(db_path: str, *, ts: str, ip_hint: str | None, endpoint: str, reason: str, meta: dict | None = None) -> int:
    """Append an abuse/guardrail event. Intended for rate limiting, payload rejections, honeypot triggers."""
    from .db import connect, init_db
    import json as _json
    meta_json = _json.dumps(meta or {}, ensure_ascii=False)
    with connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO abuse_log(ts, ip_hint, endpoint, reason, meta_json) VALUES(?,?,?,?,?)",
            (ts, ip_hint, endpoint, reason, meta_json),
        )
        conn.commit()
        return int(cur.lastrowid)

def list_abuse(
    db_path: str,
    *,
    since_ts: str | None = None,
    reason: str | None = None,
    endpoint_prefix: str | None = None,
    limit: int = 200,
) -> dict:
    """Fetch abuse_log rows + simple aggregates for operator monitoring."""
    from .db import connect, init_db
    import json as _json

    init_db(db_path)

    limit = int(limit) if limit is not None else 200
    if limit < 1:
        limit = 1
    if limit > 2000:
        limit = 2000

    where = []
    params: list = []
    if since_ts:
        where.append("ts >= ?")
        params.append(since_ts)
    if reason:
        where.append("reason = ?")
        params.append(reason)
    if endpoint_prefix:
        where.append("endpoint LIKE ?")
        params.append(f"{endpoint_prefix}%")

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    with connect(db_path) as conn:
        # recent rows
        rows = conn.execute(
            "SELECT ts, ip_hint, endpoint, reason, meta_json FROM abuse_log"
            + where_sql
            + " ORDER BY abuse_id DESC LIMIT ?",
            (*params, limit),
        ).fetchall()

        # aggregates
        by_reason = conn.execute(
            "SELECT reason, COUNT(1) FROM abuse_log" + where_sql + " GROUP BY reason ORDER BY COUNT(1) DESC",
            params,
        ).fetchall()
        by_endpoint = conn.execute(
            "SELECT endpoint, COUNT(1) FROM abuse_log" + where_sql + " GROUP BY endpoint ORDER BY COUNT(1) DESC",
            params,
        ).fetchall()
        by_ip = conn.execute(
            "SELECT IFNULL(ip_hint,''), COUNT(1) FROM abuse_log" + where_sql + " GROUP BY ip_hint ORDER BY COUNT(1) DESC LIMIT 20",
            params,
        ).fetchall()

    recent = []
    for r in rows:
        meta = {}
        try:
            meta = _json.loads(r[4] or "{}")
        except Exception:
            meta = {"_raw": r[4]}
        recent.append(
            {
                "ts": r[0],
                "ip_hint": r[1],
                "endpoint": r[2],
                "reason": r[3],
                "meta": meta,
            }
        )

    return {
        "filters": {"since_ts": since_ts, "reason": reason, "endpoint_prefix": endpoint_prefix, "limit": limit},
        "summary": {"total_recent": len(recent)},
        "by_reason": [{"reason": k, "count": int(v)} for (k, v) in by_reason],
        "by_endpoint": [{"endpoint": k, "count": int(v)} for (k, v) in by_endpoint],
        "top_ip_hints": [{"ip_hint": k, "count": int(v)} for (k, v) in by_ip],
        "recent": recent,
    }

def export_abuse_csv(
    db_path: str,
    *,
    since_ts: str | None = None,
    reason: str | None = None,
    endpoint_prefix: str | None = None,
    limit: int = 2000,
) -> str:
    """Return CSV (utf-8) for abuse_log."""
    from .db import connect, init_db
    import csv as _csv
    import io as _io

    init_db(db_path)

    limit = int(limit) if limit is not None else 2000
    if limit < 1:
        limit = 1
    if limit > 20000:
        limit = 20000

    where = []
    params: list = []
    if since_ts:
        where.append("ts >= ?")
        params.append(since_ts)
    if reason:
        where.append("reason = ?")
        params.append(reason)
    if endpoint_prefix:
        where.append("endpoint LIKE ?")
        params.append(f"{endpoint_prefix}%")

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT ts, ip_hint, endpoint, reason, meta_json FROM abuse_log"
            + where_sql
            + " ORDER BY abuse_id DESC LIMIT ?",
            (*params, limit),
        ).fetchall()

    buf = _io.StringIO()
    w = _csv.writer(buf)
    w.writerow(["ts", "ip_hint", "endpoint", "reason", "meta_json"])
    for r in rows:
        w.writerow([r[0], r[1], r[2], r[3], r[4]])
    return buf.getvalue()

