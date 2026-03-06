
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import TypeAdapter

from .db import connect, init_db, Transaction
from .models import ChatConversation

_conv_adapter = TypeAdapter(ChatConversation)


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def get_or_create_conversation(
    db_path: str,
    *,
    conversation_id: str,
    channel_id: str,
    external_thread_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    booking_id: Optional[str] = None,
    status: str = "open",
    meta_json: Optional[Dict[str, Any]] = None,
) -> ChatConversation:
    """Upsert-like create for conversation mapping.

    Idempotent on conversation_id. Uses INSERT ... ON CONFLICT DO UPDATE for atomic operation.
    """
    init_db(db_path)
    meta_json = meta_json or {}
    now = datetime.utcnow()
    now_str = _iso(now)
    con = connect(db_path)
    try:
        cur = con.cursor()
        # Use INSERT ... ON CONFLICT DO UPDATE for atomic get-or-create operation
        # This prevents race conditions where two concurrent requests both see "not exists"
        cur.execute(
            """INSERT INTO chat_conversations(
                   conversation_id, channel_id, external_thread_id, lead_id, booking_id, status, meta_json, created_at, updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?)
               ON CONFLICT(conversation_id) DO UPDATE SET
                   external_thread_id=COALESCE(excluded.external_thread_id, chat_conversations.external_thread_id),
                   lead_id=COALESCE(excluded.lead_id, chat_conversations.lead_id),
                   booking_id=COALESCE(excluded.booking_id, chat_conversations.booking_id),
                   status=excluded.status,
                   meta_json=excluded.meta_json,
                   updated_at=excluded.updated_at""",
            (
                conversation_id,
                channel_id,
                external_thread_id,
                lead_id,
                booking_id,
                status,
                json.dumps(meta_json),
                now_str,
                now_str,
            ),
        )
        con.commit()
    finally:
        con.close()
    return get_conversation(db_path, conversation_id)


def get_conversation(db_path: str, conversation_id: str) -> Optional[ChatConversation]:
    init_db(db_path)
    con = connect(db_path)
    try:
        cur = con.cursor()
        cur.execute(
            """SELECT conversation_id, channel_id, external_thread_id, lead_id, booking_id, status, meta_json, created_at, updated_at
               FROM chat_conversations WHERE conversation_id=?""",
            (conversation_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return _conv_adapter.validate_python(
            {
                "conversation_id": row[0],
                "channel_id": row[1],
                "external_thread_id": row[2],
                "lead_id": row[3],
                "booking_id": row[4],
                "status": row[5],
                "meta_json": json.loads(row[6] or "{}"),
                "created_at": datetime.fromisoformat(row[7]),
                "updated_at": datetime.fromisoformat(row[8]),
            }
        )
    finally:
        con.close()


def list_conversations(
    db_path: str,
    *,
    lead_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    client_id: Optional[str] = None,
    limit: int = 50,
) -> List[ChatConversation]:
    init_db(db_path)
    q = """SELECT c.conversation_id, c.channel_id, c.external_thread_id, c.lead_id, c.booking_id, c.status, c.meta_json, c.created_at, c.updated_at
           FROM chat_conversations c
           WHERE 1=1"""
    params: List[Any] = []
    if client_id:
        q += " AND c.lead_id IS NOT NULL AND EXISTS (SELECT 1 FROM lead_intake l WHERE l.lead_id = c.lead_id AND l.client_id = ?)"
        params.append(client_id)
    if lead_id:
        q += " AND c.lead_id=?"
        params.append(lead_id)
    if channel_id:
        q += " AND c.channel_id=?"
        params.append(channel_id)
    q += " ORDER BY c.updated_at DESC LIMIT ?"
    params.append(int(limit))

    con = connect(db_path)
    try:
        cur = con.cursor()
        cur.execute(q, tuple(params))
        rows = cur.fetchall()
        out: List[ChatConversation] = []
        for row in rows:
            out.append(
                _conv_adapter.validate_python(
                    {
                        "conversation_id": row[0],
                        "channel_id": row[1],
                        "external_thread_id": row[2],
                        "lead_id": row[3],
                        "booking_id": row[4],
                        "status": row[5],
                        "meta_json": json.loads(row[6] or "{}"),
                        "created_at": datetime.fromisoformat(row[7]),
                        "updated_at": datetime.fromisoformat(row[8]),
                    }
                )
            )
        return out
    finally:
        con.close()


def create_conversation_with_message(
    db_path: str,
    *,
    conversation_id: str,
    channel_id: str,
    external_thread_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    booking_id: Optional[str] = None,
    status: str = "open",
    meta_json: Optional[Dict[str, Any]] = None,
    message_text: Optional[str] = None,
    message_external_msg_id: Optional[str] = None,
    message_payload_json: Optional[Dict[str, Any]] = None,
    message_ts: Optional[datetime] = None,
) -> tuple[ChatConversation, Optional[str]]:
    """Create conversation and insert message atomically in a transaction.
    
    Returns (conversation, message_id) tuple.
    """
    import uuid
    from .repo_chat_messages import _iso
    
    init_db(db_path)
    meta_json = meta_json or {}
    now = datetime.utcnow()
    now_str = _iso(now)
    
    message_id = None
    if message_text is not None:
        message_id = str(uuid.uuid4())
    
    with Transaction(db_path) as con:
        cur = con.cursor()
        
        # Create/update conversation
        cur.execute(
            """INSERT INTO chat_conversations(
                   conversation_id, channel_id, external_thread_id, lead_id, booking_id, status, meta_json, created_at, updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?)
               ON CONFLICT(conversation_id) DO UPDATE SET
                   external_thread_id=COALESCE(excluded.external_thread_id, chat_conversations.external_thread_id),
                   lead_id=COALESCE(excluded.lead_id, chat_conversations.lead_id),
                   booking_id=COALESCE(excluded.booking_id, chat_conversations.booking_id),
                   status=excluded.status,
                   meta_json=excluded.meta_json,
                   updated_at=excluded.updated_at""",
            (
                conversation_id,
                channel_id,
                external_thread_id,
                lead_id,
                booking_id,
                status,
                json.dumps(meta_json),
                now_str,
                now_str,
            ),
        )
        
        # Insert message if provided
        if message_id:
            cur.execute(
                """INSERT INTO chat_messages(message_id, conversation_id, direction, ts, external_msg_id, text, payload_json)
                   VALUES(?,?,?,?,?,?,?)""",
                (
                    message_id,
                    conversation_id,
                    "inbound",
                    _iso(message_ts or now),
                    message_external_msg_id,
                    message_text,
                    json.dumps(message_payload_json or {}),
                ),
            )
        
        con.commit()
    
    conversation = get_conversation(db_path, conversation_id)
    return conversation, message_id
