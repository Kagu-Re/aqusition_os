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

def insert_lead(db_path: str, lead) -> int:
    from .db import connect, init_db
    import json as _json

    meta_json = _json.dumps(getattr(lead, "meta_json", {}) or {}, ensure_ascii=False)
    telegram_chat_id = None
    if meta_json:
        try:
            meta_dict = _json.loads(meta_json)
            telegram_chat_id = meta_dict.get("telegram_chat_id")
        except Exception:
            pass
    
    with connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO lead_intake (
                ts, source, page_id, client_id, name, phone, email, message,
                utm_source, utm_medium, utm_campaign, utm_term, utm_content,
                referrer, user_agent, ip_hint, spam_score, is_spam, status,
                booking_status, booking_value, booking_currency, booking_ts,
                telegram_chat_id, meta_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lead.ts, lead.source, lead.page_id, lead.client_id, lead.name, lead.phone, lead.email, lead.message,
                lead.utm_source, lead.utm_medium, lead.utm_campaign, lead.utm_term, lead.utm_content,
                lead.referrer, lead.user_agent, lead.ip_hint, int(lead.spam_score), int(lead.is_spam), lead.status,
                getattr(lead, 'booking_status', 'none'), getattr(lead, 'booking_value', None), getattr(lead, 'booking_currency', None), getattr(lead, 'booking_ts', None),
                telegram_chat_id, meta_json,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_lead(db_path: str, lead_id: int):
    """Fetch a single lead intake record by id."""
    from .db import connect, init_db
    import json as _json
    from .models import LeadIntake

    sql = """
    SELECT
        lead_id, ts, source, page_id, client_id, name, phone, email, message,
        utm_source, utm_medium, utm_campaign, utm_term, utm_content,
        referrer, user_agent, ip_hint, spam_score, is_spam, status,
        booking_status, booking_value, booking_currency, booking_ts,
        telegram_chat_id, meta_json
    FROM lead_intake WHERE lead_id = ?
    """
    with connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(sql, (int(lead_id),))
        r = cur.fetchone()
        if not r:
            return None
        meta = {}
        try:
            meta = _json.loads(r[25] or "{}")
        except Exception:
            meta = {}
        return LeadIntake(
            lead_id=int(r[0]),
            ts=r[1],
            source=r[2],
            page_id=r[3],
            client_id=r[4],
            name=r[5],
            phone=r[6],
            email=r[7],
            message=r[8],
            utm_source=r[9],
            utm_medium=r[10],
            utm_campaign=r[11],
            utm_term=r[12],
            utm_content=r[13],
            referrer=r[14],
            user_agent=r[15],
            ip_hint=r[16],
            spam_score=int(r[17]),
            is_spam=bool(r[18]),
            status=r[19],
            booking_status=r[20],
            booking_value=r[21],
            booking_currency=r[22],
            booking_ts=r[23],
            meta_json=meta,
        )


def get_lead_by_telegram_chat_id(db_path: str, telegram_chat_id: str):
    """Fetch a lead by Telegram chat ID using indexed column."""
    from .db import connect, init_db
    import json as _json
    from .models import LeadIntake

    sql = """
    SELECT
        lead_id, ts, source, page_id, client_id, name, phone, email, message,
        utm_source, utm_medium, utm_campaign, utm_term, utm_content,
        referrer, user_agent, ip_hint, spam_score, is_spam, status,
        booking_status, booking_value, booking_currency, booking_ts,
        telegram_chat_id, meta_json
    FROM lead_intake WHERE telegram_chat_id = ?
    """
    with connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(sql, (telegram_chat_id,))
        r = cur.fetchone()
        if not r:
            return None
        meta = {}
        try:
            meta = _json.loads(r[25] or "{}")
        except Exception:
            meta = {}
        return LeadIntake(
            lead_id=int(r[0]),
            ts=r[1],
            source=r[2],
            page_id=r[3],
            client_id=r[4],
            name=r[5],
            phone=r[6],
            email=r[7],
            message=r[8],
            utm_source=r[9],
            utm_medium=r[10],
            utm_campaign=r[11],
            utm_term=r[12],
            utm_content=r[13],
            referrer=r[14],
            user_agent=r[15],
            ip_hint=r[16],
            spam_score=int(r[17]),
            is_spam=bool(r[18]),
            status=r[19],
            booking_status=r[20],
            booking_value=r[21],
            booking_currency=r[22],
            booking_ts=r[23],
            meta_json=meta,
        )


def get_or_create_lead_by_telegram_chat_id(
    db_path: str,
    telegram_chat_id: str,
    username: Optional[str] = None,
    client_id: Optional[str] = None,
    source: str = "telegram_bot",
) -> int:
    """Get or create a lead by Telegram chat ID atomically.
    
    Uses INSERT OR IGNORE pattern to prevent race conditions.
    Returns the lead_id of the existing or newly created lead.
    """
    from .db import connect, init_db
    from datetime import datetime, timezone
    import json as _json
    
    init_db(db_path)
    
    # First try to get existing lead
    existing = get_lead_by_telegram_chat_id(db_path, telegram_chat_id)
    if existing:
        return existing.lead_id
    
    # Try to create new lead atomically
    now = datetime.now(timezone.utc).isoformat()
    name = username or f"Telegram User {telegram_chat_id}"
    meta_json = {
        "telegram_chat_id": telegram_chat_id,
        "telegram_username": username
    }
    meta_json_str = _json.dumps(meta_json, ensure_ascii=False)
    
    with connect(db_path) as conn:
        cur = conn.cursor()
        # Use INSERT OR IGNORE to handle race condition
        # If another process creates the lead between our check and insert, this will ignore
        cur.execute(
            """
            INSERT OR IGNORE INTO lead_intake (
                ts, source, client_id, name, telegram_chat_id, status,
                booking_status, meta_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now, source, client_id, name, telegram_chat_id,
                "new", "none", meta_json_str
            ),
        )
        conn.commit()
        
        # Get the lead_id (either from our insert or existing one)
        cur.execute(
            "SELECT lead_id FROM lead_intake WHERE telegram_chat_id = ?",
            (telegram_chat_id,)
        )
        row = cur.fetchone()
        if row:
            return int(row[0])
        
        # This should not happen, but handle edge case
        raise Exception(f"Failed to create or retrieve lead for telegram_chat_id: {telegram_chat_id}")

def list_leads(
    db_path: str,
    *,
    limit: int = 200,
    status: str | None = None,
    is_spam: int | None = None,
    client_id: str | None = None,
    page_id: str | None = None,
):
    from .db import connect, init_db
    import json as _json
    from .models import LeadIntake

    where = []
    params = []
    if status:
        where.append("status = ?")
        params.append(status)
    if is_spam is not None:
        where.append("is_spam = ?")
        params.append(int(is_spam))
    if client_id:
        where.append("client_id = ?")
        params.append(client_id)
    if page_id:
        where.append("page_id = ?")
        params.append(page_id)

    w = (" WHERE " + " AND ".join(where)) if where else ""
    sql = (
        "SELECT lead_id, ts, source, page_id, client_id, name, phone, email, message, "
        "utm_source, utm_medium, utm_campaign, utm_term, utm_content, referrer, user_agent, ip_hint, "
        "spam_score, is_spam, status, booking_status, booking_value, booking_currency, booking_ts, "
        "telegram_chat_id, meta_json "
        "FROM lead_intake"
        f"{w} ORDER BY lead_id DESC LIMIT ?"
    )
    params.append(int(limit))
    with connect(db_path) as conn:
        cur = conn.cursor()
        rows = cur.execute(sql, params).fetchall()

    items = []
    for r in rows:
        try:
            meta = _json.loads(r[25] or "{}")
        except Exception:
            meta = {}
        items.append(
            LeadIntake(
                lead_id=r[0],
                ts=r[1],
                source=r[2],
                page_id=r[3],
                client_id=r[4],
                name=r[5],
                phone=r[6],
                email=r[7],
                message=r[8],
                utm_source=r[9],
                utm_medium=r[10],
                utm_campaign=r[11],
                utm_term=r[12],
                utm_content=r[13],
                referrer=r[14],
                user_agent=r[15],
                ip_hint=r[16],
                spam_score=int(r[17] or 0),
                is_spam=int(r[18] or 0),
                status=r[19] or "new",
                booking_status=r[20] or "none",
                booking_value=r[21],
                booking_currency=r[22],
                booking_ts=r[23],
                meta_json=meta,
            )
        )
    return items

def update_lead_outcome(
    db_path: str,
    lead_id: int,
    *,
    status: str | None = None,
    booking_status: str | None = None,
    booking_value: float | None = None,
    booking_currency: str | None = None,
    booking_ts: str | None = None,
) -> None:
    from .db import connect, init_db
    fields = []
    params = []
    if status is not None:
        fields.append("status = ?")
        params.append(status)
    if booking_status is not None:
        fields.append("booking_status = ?")
        params.append(booking_status)
    if booking_value is not None:
        fields.append("booking_value = ?")
        params.append(float(booking_value))
    if booking_currency is not None:
        fields.append("booking_currency = ?")
        params.append(booking_currency)
    if booking_ts is not None:
        fields.append("booking_ts = ?")
        params.append(booking_ts)

    if not fields:
        return

    params.append(int(lead_id))
    sql = f"UPDATE lead_intake SET {', '.join(fields)} WHERE lead_id = ?"
    with connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()

