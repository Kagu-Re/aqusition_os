
from __future__ import annotations

from typing import Optional, Any, Dict, List

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from .console_support import require_role, _resolve_db_path
from .audit import audit_event
from .tenant.context import get_scoped_client_id
from .repo_chat_conversations import get_or_create_conversation, get_conversation, list_conversations
from .repo_chat_messages import insert_message, list_messages
from .event_bus import EventBus

admin_router = APIRouter(prefix="/api/chat", tags=["chat"])


def _effective_client_id(request: Request) -> str | None:
    return get_scoped_client_id(request)


class ConversationUpsertIn(BaseModel):
    conversation_id: str = Field(min_length=1)
    channel_id: str = Field(min_length=1)
    external_thread_id: Optional[str] = None
    lead_id: Optional[str] = None
    booking_id: Optional[str] = None
    status: str = "open"
    meta_json: Dict[str, Any] = Field(default_factory=dict)


@admin_router.get("/conversations")
def api_list_conversations(
    request: Request,
    db: Optional[str] = None,
    lead_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    limit: int = 50,
    _user=Depends(require_role("operator")),
):
    db_path = _resolve_db_path(db, request)
    client_id = _effective_client_id(request)
    return {"items": list_conversations(db_path, lead_id=lead_id, channel_id=channel_id, client_id=client_id, limit=limit)}


@admin_router.get("/conversations/{conversation_id}")
def api_get_conversation(
    conversation_id: str,
    request: Request,
    db: Optional[str] = None,
    _user=Depends(require_role("operator")),
):
    from fastapi import HTTPException
    from .repo_leads import get_lead

    db_path = _resolve_db_path(db, request)
    conv = get_conversation(db_path, conversation_id)
    if not conv:
        return {"error": "not_found"}
    client_id = _effective_client_id(request)
    if client_id and conv.lead_id:
        try:
            lead = get_lead(db_path, int(conv.lead_id))
            if lead and getattr(lead, "client_id", None) != client_id:
                raise HTTPException(status_code=403, detail="forbidden")
        except ValueError:
            pass
    return conv


@admin_router.post("/conversations")
def api_upsert_conversation(
    body: ConversationUpsertIn,
    request: Request,
    db: Optional[str] = None,
    _user=Depends(require_role("operator")),
):
    db_path = _resolve_db_path(db, request)
    conv = get_or_create_conversation(
        db_path,
        conversation_id=body.conversation_id,
        channel_id=body.channel_id,
        external_thread_id=body.external_thread_id,
        lead_id=body.lead_id,
        booking_id=body.booking_id,
        status=body.status,
        meta_json=body.meta_json,
    )
    audit_event("chat_conversation_upsert", request=request, meta={"conversation_id": conv.conversation_id})
    # best-effort emit opened (idempotency is caller's responsibility in v1)
    try:
        EventBus.emit_topic(
            db_path,
            topic="op.chat.conversation_opened",
            aggregate_type="chat",
            aggregate_id=conv.conversation_id,
            payload={"conversation_id": conv.conversation_id, "lead_id": conv.lead_id},
        )
    except Exception:
        pass
    return conv


class MessageIn(BaseModel):
    direction: str = Field(default="inbound")  # inbound|outbound
    text: str = Field(default="")
    external_msg_id: Optional[str] = None
    payload_json: Dict[str, Any] = Field(default_factory=dict)


@admin_router.post("/conversations/{conversation_id}/messages")
def api_add_message(
    conversation_id: str,
    body: MessageIn,
    request: Request,
    db: Optional[str] = None,
    _user=Depends(require_role("operator")),
):
    db_path = _resolve_db_path(db, request)
    msg = insert_message(
        db_path,
        conversation_id=conversation_id,
        direction=body.direction,
        text=body.text,
        external_msg_id=body.external_msg_id,
        payload_json=body.payload_json,
    )
    audit_event("chat_message_insert", request=request, meta={"conversation_id": conversation_id, "direction": body.direction})
    topic = "op.chat.message_received" if body.direction == "inbound" else "op.chat.message_sent"
    try:
        EventBus.emit_topic(
            db_path,
            topic=topic,
            aggregate_type="chat",
            aggregate_id=conversation_id,
            payload={"conversation_id": conversation_id, "text": body.text},
        )
    except Exception:
        pass
    return msg


@admin_router.get("/conversations/{conversation_id}/messages")
def api_list_messages(
    conversation_id: str,
    request: Request,
    db: Optional[str] = None,
    limit: int = 200,
    _user=Depends(require_role("operator")),
):
    db_path = _resolve_db_path(db, request)
    return {"items": list_messages(db_path, conversation_id=conversation_id, limit=limit)}
