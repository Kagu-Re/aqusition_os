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

_adstat_adapter = TypeAdapter(AdStat)

def insert_ad_stat(db_path: str, stat: AdStat) -> None:
    con = db.connect(db_path)
    try:
        con.execute(
            """INSERT INTO ad_stats(stat_id, timestamp, page_id, platform, campaign_id, adset_id, ad_id, impressions, clicks, spend, revenue)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                stat.stat_id,
                stat.timestamp.isoformat(),
                stat.page_id,
                stat.platform,
                stat.campaign_id,
                stat.adset_id,
                stat.ad_id,
                stat.impressions,
                stat.clicks,
                stat.spend,
                stat.revenue,
            ),
        )
        con.commit()
    finally:
        con.close()

def sum_ad_stats(
    db_path: str,
    page_id: str,
    since_iso: str | None = None,
    platform: str | None = None,
) -> dict:
    con = db.connect(db_path)
    try:
        where = ["page_id=?"]
        params = [page_id]
        if since_iso:
            where.append("timestamp>=?")
            params.append(since_iso)
        if platform:
            where.append("platform=?")
            params.append(platform)
        sql = f"""SELECT
            SUM(COALESCE(impressions,0)) as impressions,
            SUM(COALESCE(clicks,0)) as clicks,
            SUM(COALESCE(spend,0.0)) as spend,
            SUM(COALESCE(revenue,0.0)) as revenue
        FROM ad_stats
        WHERE {' AND '.join(where)}"""
        row = db.fetchone(con, sql, tuple(params))
        if not row:
            return {}
        return {
            "impressions": row["impressions"],
            "clicks": row["clicks"],
            "spend": row["spend"],
            "revenue": row["revenue"],
        }
    finally:
        con.close()

# --- Activity Log (append-only) ---

def revenue_stats(db_path: str, *, client_id: str | None = None) -> dict:
    """Minimal aggregation for operator visibility. Assumes booking_value is the revenue signal.
    When client_id is set, filters lead_intake by client_id."""
    from .db import connect, init_db

    w = " AND client_id = ?" if client_id else ""
    params = [client_id] if client_id else []
    with connect(db_path) as conn:
        cur = conn.cursor()
        total = cur.execute(
            "SELECT COUNT(*), COALESCE(SUM(booking_value), 0) FROM lead_intake WHERE booking_status IN ('booked','paid') AND is_spam = 0" + w,
            params,
        ).fetchone()
        by_source = cur.execute(
            "SELECT COALESCE(source,'unknown') as source, COUNT(*), COALESCE(SUM(booking_value), 0) "
            "FROM lead_intake WHERE booking_status IN ('booked','paid') AND is_spam = 0" + w + " GROUP BY source ORDER BY 3 DESC",
            params,
        ).fetchall()
        by_campaign = cur.execute(
            "SELECT COALESCE(utm_campaign,'') as utm_campaign, COUNT(*), COALESCE(SUM(booking_value), 0) "
            "FROM lead_intake WHERE booking_status IN ('booked','paid') AND is_spam = 0" + w + " GROUP BY utm_campaign ORDER BY 3 DESC LIMIT 50",
            params,
        ).fetchall()

    return {
        "total": {"count": int(total[0] or 0), "value": float(total[1] or 0)},
        "by_source": [{"source": r[0], "count": int(r[1] or 0), "value": float(r[2] or 0)} for r in by_source],
        "by_campaign": [{"utm_campaign": r[0], "count": int(r[1] or 0), "value": float(r[2] or 0)} for r in by_campaign],
    }

# --- Ad spend ---

def insert_spend_daily(
    db_path: str,
    *,
    day: str,
    source: str,
    spend_value: float,
    spend_currency: str = "THB",
    utm_campaign: str | None = None,
    client_id: str | None = None,
    meta_json: dict | None = None,
) -> int:
    from .db import connect, init_db
    import json as _json
    from datetime import datetime

    ts = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    meta = _json.dumps(meta_json or {}, ensure_ascii=False)
    with connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO ad_spend_daily (
                ts, day, source, utm_campaign, client_id, spend_value, spend_currency, meta_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ts, day, source, utm_campaign, client_id, float(spend_value), spend_currency, meta),
        )
        conn.commit()
        return int(cur.lastrowid)

def list_spend_daily(
    db_path: str,
    *,
    day_from: str | None = None,
    day_to: str | None = None,
    source: str | None = None,
    utm_campaign: str | None = None,
    client_id: str | None = None,
    limit: int = 500,
):
    from .db import connect, init_db
    import json as _json

    where = []
    params = []
    if day_from:
        where.append("day >= ?")
        params.append(day_from)
    if day_to:
        where.append("day <= ?")
        params.append(day_to)
    if source:
        where.append("source = ?")
        params.append(source)
    if utm_campaign:
        where.append("utm_campaign = ?")
        params.append(utm_campaign)
    if client_id:
        where.append("client_id = ?")
        params.append(client_id)

    w = (" WHERE " + " AND ".join(where)) if where else ""
    sql = (
        "SELECT spend_id, ts, day, source, utm_campaign, client_id, spend_value, spend_currency, meta_json "
        "FROM ad_spend_daily"
        f"{w} ORDER BY day DESC, spend_id DESC LIMIT ?"
    )
    params.append(int(limit))

    with connect(db_path) as conn:
        cur = conn.cursor()
        rows = cur.execute(sql, params).fetchall()

    items = []
    for r in rows:
        try:
            meta = _json.loads(r[8] or "{}")
        except Exception:
            meta = {}
        items.append(
            {
                "spend_id": int(r[0]),
                "ts": r[1],
                "day": r[2],
                "source": r[3],
                "utm_campaign": r[4],
                "client_id": r[5],
                "spend_value": float(r[6]),
                "spend_currency": r[7],
                "meta_json": meta,
            }
        )
    return items

def roas_stats(db_path: str, *, client_id: str | None = None) -> dict:
    """Compute minimal ROAS using booked/paid revenue vs imported spend.
    When client_id is set, filters lead_intake and ad_spend_daily by client_id."""
    from .db import connect, init_db

    w_lead = " AND client_id = ?" if client_id else ""
    w_spend = " WHERE client_id = ?" if client_id else ""
    params = [client_id] if client_id else []
    with connect(db_path) as conn:
        cur = conn.cursor()

        # spend totals
        spend_total = cur.execute(
            "SELECT COALESCE(SUM(spend_value), 0) FROM ad_spend_daily" + w_spend,
            params,
        ).fetchone()[0] or 0.0

        spend_by_source = cur.execute(
            "SELECT source, COALESCE(SUM(spend_value), 0) FROM ad_spend_daily" + w_spend + " GROUP BY source ORDER BY 2 DESC",
            params,
        ).fetchall()

        spend_by_campaign = cur.execute(
            "SELECT COALESCE(utm_campaign,''), COALESCE(SUM(spend_value), 0) FROM ad_spend_daily" + w_spend + " GROUP BY utm_campaign ORDER BY 2 DESC LIMIT 100",
            params,
        ).fetchall()

        # revenue totals (from lead_intake)
        rev_total = cur.execute(
            "SELECT COALESCE(SUM(booking_value), 0) FROM lead_intake WHERE booking_status IN ('booked','paid') AND is_spam = 0" + w_lead,
            params,
        ).fetchone()[0] or 0.0

        rev_by_source = cur.execute(
            "SELECT COALESCE(source,'unknown'), COALESCE(SUM(booking_value), 0) "
            "FROM lead_intake WHERE booking_status IN ('booked','paid') AND is_spam = 0" + w_lead + " GROUP BY source ORDER BY 2 DESC",
            params,
        ).fetchall()

        rev_by_campaign = cur.execute(
            "SELECT COALESCE(utm_campaign,''), COALESCE(SUM(booking_value), 0) "
            "FROM lead_intake WHERE booking_status IN ('booked','paid') AND is_spam = 0" + w_lead + " GROUP BY utm_campaign ORDER BY 2 DESC LIMIT 100",
            params,
        ).fetchall()

    def _mk(rows, key):
        return {r[0] or "": float(r[1] or 0.0) for r in rows}

    spend_src = _mk(spend_by_source, 0)
    spend_cmp = _mk(spend_by_campaign, 0)
    rev_src = _mk(rev_by_source, 0)
    rev_cmp = _mk(rev_by_campaign, 0)

    def _roas(rev, spend):
        return (rev / spend) if spend and spend > 0 else None

    # Join keys
    src_keys = sorted(set(spend_src.keys()) | set(rev_src.keys()))
    cmp_keys = sorted(set(spend_cmp.keys()) | set(rev_cmp.keys()))

    return {
        "total": {"revenue": float(rev_total), "spend": float(spend_total), "roas": _roas(float(rev_total), float(spend_total))},
        "by_source": [
            {"source": k, "revenue": float(rev_src.get(k, 0.0)), "spend": float(spend_src.get(k, 0.0)), "roas": _roas(float(rev_src.get(k, 0.0)), float(spend_src.get(k, 0.0)))}
            for k in src_keys
        ],
        "by_campaign": [
            {"utm_campaign": k, "revenue": float(rev_cmp.get(k, 0.0)), "spend": float(spend_cmp.get(k, 0.0)), "roas": _roas(float(rev_cmp.get(k, 0.0)), float(spend_cmp.get(k, 0.0)))}
            for k in cmp_keys if k is not None
        ],
    }

def upsert_spend_daily(
    db_path: str,
    *,
    day: str,
    source: str,
    spend_value: float,
    spend_currency: str = "THB",
    utm_campaign: str | None = None,
    client_id: str | None = None,
    meta_json: dict | None = None,
) -> dict:
    """Upsert by natural key (day, source, utm_campaign, client_id, spend_currency).
    If row exists -> overwrite spend_value and meta_json; else insert new.
    Returns {"action": "insert"|"update", "spend_id": int}.
    """
    from .db import connect, init_db
    import json as _json
    from datetime import datetime

    ts = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    meta = _json.dumps(meta_json or {}, ensure_ascii=False)

    key = (day, source, utm_campaign, client_id, spend_currency)
    with connect(db_path) as conn:
        cur = conn.cursor()
        row = cur.execute(
            "SELECT spend_id FROM ad_spend_daily WHERE day = ? AND source = ? AND "
            "COALESCE(utm_campaign,'') = COALESCE(?, '') AND COALESCE(client_id,'') = COALESCE(?, '') AND spend_currency = ? "
            "ORDER BY spend_id DESC LIMIT 1",
            (day, source, utm_campaign, client_id, spend_currency),
        ).fetchone()
        if row:
            spend_id = int(row[0])
            cur.execute(
                "UPDATE ad_spend_daily SET ts = ?, spend_value = ?, meta_json = ? WHERE spend_id = ?",
                (ts, float(spend_value), meta, spend_id),
            )
            conn.commit()
            return {"action": "update", "spend_id": spend_id}
        else:
            cur.execute(
                """
                INSERT INTO ad_spend_daily (
                    ts, day, source, utm_campaign, client_id, spend_value, spend_currency, meta_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (ts, day, source, utm_campaign, client_id, float(spend_value), spend_currency, meta),
            )
            conn.commit()
            return {"action": "insert", "spend_id": int(cur.lastrowid)}

def update_spend_daily(
    db_path: str,
    spend_id: int,
    *,
    day: str | None = None,
    source: str | None = None,
    utm_campaign: str | None = None,
    client_id: str | None = None,
    spend_value: float | None = None,
    spend_currency: str | None = None,
) -> None:
    from .db import connect, init_db
    from datetime import datetime

    fields = []
    params = []
    if day is not None:
        fields.append("day = ?")
        params.append(day)
    if source is not None:
        fields.append("source = ?")
        params.append(source)
    if utm_campaign is not None:
        fields.append("utm_campaign = ?")
        params.append(utm_campaign)
    if client_id is not None:
        fields.append("client_id = ?")
        params.append(client_id)
    if spend_value is not None:
        fields.append("spend_value = ?")
        params.append(float(spend_value))
    if spend_currency is not None:
        fields.append("spend_currency = ?")
        params.append(spend_currency)

    if not fields:
        return

    ts = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    fields.insert(0, "ts = ?")
    params.insert(0, ts)

    params.append(int(spend_id))
    sql = f"UPDATE ad_spend_daily SET {', '.join(fields)} WHERE spend_id = ?"
    with connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()

