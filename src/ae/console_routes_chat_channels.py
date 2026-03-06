from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field

from .console_support import require_role, _resolve_db_path
from .audit import audit_event
from .tenant.context import get_scoped_client_id
from . import repo
from .enums import ChatProvider


admin_router = APIRouter()


def _effective_client_id(request: Request) -> str | None:
    return get_scoped_client_id(request)


class ChatChannelUpsertIn(BaseModel):
    channel_id: str = Field(min_length=1)
    provider: ChatProvider = ChatProvider.other
    handle: str = Field(min_length=1)
    display_name: Optional[str] = None
    meta_json: Dict[str, Any] = Field(default_factory=dict)


class ChatChannelUpdateIn(BaseModel):
    provider: Optional[ChatProvider] = None
    handle: Optional[str] = Field(default=None, min_length=1)
    display_name: Optional[str] = None
    meta_json: Optional[Dict[str, Any]] = None


@admin_router.get("/api/chat/channels")
def list_channels(
    request: Request,
    provider: Optional[ChatProvider] = None,
    limit: int = 200,
    _=Depends(require_role("operator")),
):
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    client_id = _effective_client_id(request)
    return repo.list_chat_channels(db_path, provider=provider, client_id=client_id, limit=limit)


@admin_router.get("/api/chat/channels/{channel_id}")
def get_channel(channel_id: str, request: Request, _=Depends(require_role("operator"))):
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    ch = repo.get_chat_channel(db_path, channel_id)
    if not ch:
        return {"ok": False, "error": "not_found"}
    client_id = _effective_client_id(request)
    if client_id and (ch.meta_json or {}).get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="forbidden")
    return ch


@admin_router.post("/api/chat/channels")
def upsert_channel(payload: ChatChannelUpsertIn, request: Request, _=Depends(require_role("operator"))):
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    ch = repo.upsert_chat_channel(
        db_path,
        channel_id=payload.channel_id,
        provider=payload.provider,
        handle=payload.handle,
        display_name=payload.display_name,
        meta_json=payload.meta_json or {},
    )
    audit_event(
        "chat_channel_upsert",
        request,
        meta={"entity_type": "chat_channel", "entity_id": ch.channel_id, "provider": ch.provider.value},
    )
    return ch


@admin_router.put("/api/chat/channels/{channel_id}")
def update_channel(
    channel_id: str,
    payload: ChatChannelUpdateIn,
    request: Request,
    _=Depends(require_role("operator")),
):
    """Update an existing chat channel."""
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    existing = repo.get_chat_channel(db_path, channel_id)
    if not existing:
        raise HTTPException(status_code=404, detail="channel_not_found")
    client_id = _effective_client_id(request)
    if client_id and (existing.meta_json or {}).get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="forbidden")
    
    ch = repo.upsert_chat_channel(
        db_path,
        channel_id=channel_id,
        provider=payload.provider if payload.provider else existing.provider,
        handle=payload.handle if payload.handle else existing.handle,
        display_name=payload.display_name if payload.display_name is not None else existing.display_name,
        meta_json=payload.meta_json if payload.meta_json is not None else existing.meta_json,
        created_at=existing.created_at,  # Preserve original created_at
    )
    audit_event(
        "chat_channel_update",
        request,
        meta={"entity_type": "chat_channel", "entity_id": channel_id, "provider": ch.provider.value},
    )
    return ch


@admin_router.delete("/api/chat/channels/{channel_id}")
def delete_channel(
    channel_id: str,
    request: Request,
    _=Depends(require_role("operator")),
):
    """Delete a chat channel."""
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    existing = repo.get_chat_channel(db_path, channel_id)
    if not existing:
        raise HTTPException(status_code=404, detail="channel_not_found")
    client_id = _effective_client_id(request)
    if client_id and (existing.meta_json or {}).get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="forbidden")
    
    repo.delete_chat_channel(db_path, channel_id)
    audit_event(
        "chat_channel_delete",
        request,
        meta={"entity_type": "chat_channel", "entity_id": channel_id},
    )
    return {"ok": True, "channel_id": channel_id}
