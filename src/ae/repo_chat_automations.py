
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .db import connect, init_db
from .models import ChatAutomation


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def create_automation(
    db_path: str,
    *,
    conversation_id: str,
    template_key: str,
    due_at: datetime,
    context_json: Optional[Dict[str, Any]] = None,
) -> ChatAutomation:
    init_db(db_path)
    now = datetime.utcnow()
    automation_id = str(uuid.uuid4())
    context_json = context_json or {}
    con = connect(db_path)
    try:
        cur = con.cursor()
        cur.execute(
            """INSERT INTO chat_automations(automation_id, conversation_id, template_key, due_at, status, context_json, created_at, sent_at)
               VALUES(?,?,?,?,?,?,?,NULL)""",
            (
                automation_id,
                conversation_id,
                template_key,
                _iso(due_at),
                "pending",
                json.dumps(context_json),
                _iso(now),
            ),
        )
        con.commit()
    finally:
        con.close()
    return ChatAutomation(
        automation_id=automation_id,
        conversation_id=conversation_id,
        template_key=template_key,
        due_at=due_at,
        status="pending",
        context_json=context_json,
        created_at=now,
        sent_at=None,
    )


def list_due_automations(
    db_path: str,
    *,
    now: datetime,
    limit: int = 50,
) -> List[ChatAutomation]:
    init_db(db_path)
    con = connect(db_path)
    try:
        cur = con.cursor()
        cur.execute(
            """SELECT automation_id, conversation_id, template_key, due_at, status, context_json, created_at, sent_at
               FROM chat_automations
               WHERE status='pending' AND due_at <= ?
               ORDER BY due_at ASC
               LIMIT ?""",
            (_iso(now), int(limit)),
        )
        rows = cur.fetchall()
        out: List[ChatAutomation] = []
        for r in rows:
            out.append(
                ChatAutomation(
                    automation_id=r[0],
                    conversation_id=r[1],
                    template_key=r[2],
                    due_at=datetime.fromisoformat(r[3]),
                    status=r[4],
                    context_json=json.loads(r[5] or "{}"),
                    created_at=datetime.fromisoformat(r[6]),
                    sent_at=datetime.fromisoformat(r[7]) if r[7] else None,
                )
            )
        return out
    finally:
        con.close()


def mark_sent(db_path: str, automation_id: str, sent_at: datetime) -> None:
    init_db(db_path)
    con = connect(db_path)
    try:
        cur = con.cursor()
        cur.execute(
            """UPDATE chat_automations SET status='sent', sent_at=? WHERE automation_id=?""",
            (_iso(sent_at), automation_id),
        )
        con.commit()
    finally:
        con.close()


def list_automations(
    db_path: str,
    *,
    status: Optional[str] = None,
    limit: int = 200,
) -> List[ChatAutomation]:
    init_db(db_path)
    q = """SELECT automation_id, conversation_id, template_key, due_at, status, context_json, created_at, sent_at
           FROM chat_automations WHERE 1=1"""
    params: List[Any] = []
    if status:
        q += " AND status=?"
        params.append(status)
    q += " ORDER BY created_at DESC LIMIT ?"
    params.append(int(limit))
    con = connect(db_path)
    try:
        cur = con.cursor()
        cur.execute(q, tuple(params))
        rows = cur.fetchall()
        return [
            ChatAutomation(
                automation_id=r[0],
                conversation_id=r[1],
                template_key=r[2],
                due_at=datetime.fromisoformat(r[3]),
                status=r[4],
                context_json=json.loads(r[5] or "{}"),
                created_at=datetime.fromisoformat(r[6]),
                sent_at=datetime.fromisoformat(r[7]) if r[7] else None,
            )
            for r in rows
        ]
    finally:
        con.close()
