from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import TypeAdapter

from . import db
from .enums import ChatProvider
from .models import ChatChannel


_channel_adapter = TypeAdapter(ChatChannel)


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def upsert_chat_channel(
    db_path: str,
    *,
    channel_id: str,
    provider: ChatProvider,
    handle: str,
    display_name: Optional[str] = None,
    meta_json: Optional[Dict[str, Any]] = None,
    created_at: Optional[datetime] = None,
) -> ChatChannel:
    """Create or update a chat channel entry.

    v1: channel registry only. Does not store messages.
    """

    if not channel_id or not channel_id.strip():
        raise ValueError("channel_id required")
    if not handle or not handle.strip():
        raise ValueError("handle required")
    meta_json = meta_json or {}
    created_at = created_at or datetime.utcnow()

    con = db.connect(db_path)
    try:
        con.execute(
            """INSERT INTO chat_channels(channel_id, provider, handle, display_name, meta_json, created_at)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(channel_id) DO UPDATE SET
                    provider=excluded.provider,
                    handle=excluded.handle,
                    display_name=excluded.display_name,
                    meta_json=excluded.meta_json
            """,
            (
                channel_id.strip(),
                provider.value,
                handle.strip(),
                (display_name or None),
                json.dumps(meta_json),
                _iso(created_at),
            ),
        )
        con.commit()
    finally:
        con.close()

    ch = get_chat_channel(db_path, channel_id)
    if not ch:
        raise ValueError("failed to upsert chat channel")
    return ch


def get_chat_channel(db_path: str, channel_id: str) -> Optional[ChatChannel]:
    con = db.connect(db_path)
    try:
        row = db.fetchone(con, "SELECT * FROM chat_channels WHERE channel_id=?", (channel_id,))
        if not row:
            return None
        d = dict(row)
        d["provider"] = d["provider"]
        d["meta_json"] = json.loads(d.get("meta_json") or "{}")
        d["created_at"] = datetime.fromisoformat(d["created_at"]) if d.get("created_at") else datetime.utcnow()
        return _channel_adapter.validate_python(d)
    finally:
        con.close()


def list_chat_channels(
    db_path: str,
    *,
    provider: Optional[ChatProvider] = None,
    client_id: Optional[str] = None,
    limit: int = 200,
) -> List[ChatChannel]:
    limit = max(1, min(int(limit), 2000))

    con = db.connect(db_path)
    try:
        conds: List[str] = []
        params: List[Any] = []
        if provider:
            conds.append("provider=?")
            params.append(provider.value)
        if client_id:
            conds.append("json_extract(meta_json, '$.client_id') = ?")
            params.append(client_id)
        where = (" WHERE " + " AND ".join(conds)) if conds else ""
        params.append(limit)
        rows = con.execute(
            f"SELECT * FROM chat_channels{where} ORDER BY created_at DESC LIMIT ?",
            tuple(params),
        ).fetchall()

        out: List[ChatChannel] = []
        for r in rows:
            d = dict(r)
            d["meta_json"] = json.loads(d.get("meta_json") or "{}")
            d["created_at"] = datetime.fromisoformat(d["created_at"]) if d.get("created_at") else datetime.utcnow()
            out.append(_channel_adapter.validate_python(d))
        return out
    finally:
        con.close()


def delete_chat_channel(db_path: str, channel_id: str) -> None:
    """Delete a chat channel."""
    con = db.connect(db_path)
    try:
        con.execute("DELETE FROM chat_channels WHERE channel_id=?", (channel_id,))
        con.commit()
    finally:
        con.close()
