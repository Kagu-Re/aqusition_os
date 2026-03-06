
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import TypeAdapter

from .db import connect, init_db
from .models import ChatMessage

_msg_adapter = TypeAdapter(ChatMessage)


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def insert_message(
    db_path: str,
    *,
    conversation_id: str,
    direction: str,
    text: Optional[str] = None,
    external_msg_id: Optional[str] = None,
    payload_json: Optional[Dict[str, Any]] = None,
    ts: Optional[datetime] = None,
) -> ChatMessage:
    init_db(db_path)
    payload_json = payload_json or {}
    ts = ts or datetime.utcnow()
    message_id = str(uuid.uuid4())

    con = connect(db_path)
    try:
        cur = con.cursor()
        cur.execute(
            """INSERT INTO chat_messages(message_id, conversation_id, direction, ts, external_msg_id, text, payload_json)
               VALUES(?,?,?,?,?,?,?)""",
            (
                message_id,
                conversation_id,
                direction,
                _iso(ts),
                external_msg_id,
                text,
                json.dumps(payload_json),
            ),
        )
        con.commit()
    finally:
        con.close()

    return _msg_adapter.validate_python(
        {
            "message_id": message_id,
            "conversation_id": conversation_id,
            "direction": direction,
            "ts": ts,
            "external_msg_id": external_msg_id,
            "text": text,
            "payload_json": payload_json,
        }
    )


def list_messages(
    db_path: str,
    *,
    conversation_id: str,
    limit: int = 200,
) -> List[ChatMessage]:
    init_db(db_path)
    con = connect(db_path)
    try:
        cur = con.cursor()
        cur.execute(
            """SELECT message_id, conversation_id, direction, ts, external_msg_id, text, payload_json
               FROM chat_messages WHERE conversation_id=?
               ORDER BY ts ASC LIMIT ?""",
            (conversation_id, int(limit)),
        )
        rows = cur.fetchall()
        out: List[ChatMessage] = []
        for row in rows:
            out.append(
                _msg_adapter.validate_python(
                    {
                        "message_id": row[0],
                        "conversation_id": row[1],
                        "direction": row[2],
                        "ts": datetime.fromisoformat(row[3]),
                        "external_msg_id": row[4],
                        "text": row[5],
                        "payload_json": json.loads(row[6] or "{}"),
                    }
                )
            )
        return out
    finally:
        con.close()
