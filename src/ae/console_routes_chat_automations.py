
from __future__ import annotations

from typing import Optional, Any, Dict

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from .console_support import require_role, _resolve_db_path
from .audit import audit_event
from .repo_chat_automations import list_automations, create_automation
from .chat_automation import run_due_chat_automations

admin_router = APIRouter(prefix="/api/chat", tags=["chat"])


@admin_router.get("/automations")
def api_list_automations(
    request: Request,
    db: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200,
    _user=Depends(require_role("operator")),
):
    db_path = _resolve_db_path(db, request)
    return {"items": list_automations(db_path, status=status, limit=limit)}


class AutomationCreateIn(BaseModel):
    conversation_id: str = Field(min_length=1)
    template_key: str = Field(min_length=1)
    due_in_seconds: int = 0
    context_json: Dict[str, Any] = Field(default_factory=dict)


@admin_router.post("/automations")
def api_create_automation(
    body: AutomationCreateIn,
    request: Request,
    db: Optional[str] = None,
    _user=Depends(require_role("operator")),
):
    from datetime import datetime, timedelta
    db_path = _resolve_db_path(db, request)
    a = create_automation(
        db_path,
        conversation_id=body.conversation_id,
        template_key=body.template_key,
        due_at=datetime.utcnow() + timedelta(seconds=int(body.due_in_seconds)),
        context_json=body.context_json,
    )
    audit_event("chat_automation_create", request=request, meta={"conversation_id": a.conversation_id, "template_key": a.template_key})
    return a


@admin_router.post("/automations/run")
def api_run_automations(
    request: Request,
    db: Optional[str] = None,
    limit: int = 50,
    _user=Depends(require_role("operator")),
):
    db_path = _resolve_db_path(db, request)
    sent = run_due_chat_automations(db_path, limit=limit)
    audit_event("chat_automation_run", request=request, meta={"sent": sent})
    return {"sent": sent}
