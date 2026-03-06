
from __future__ import annotations

from typing import Optional, Any, Dict

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from .console_support import require_role, _resolve_db_path
from .audit import audit_event
from .models import ChatTemplate
from .repo_chat_templates import upsert_template, list_templates

admin_router = APIRouter(prefix="/api/chat", tags=["chat"])


class TemplateUpsertIn(BaseModel):
    template_key: str = Field(min_length=1)
    language: str = "en"
    body: str = Field(min_length=1)
    status: str = "active"


@admin_router.get("/templates")
def api_list_templates(
    request: Request,
    db: Optional[str] = None,
    limit: int = 200,
    _user=Depends(require_role("operator")),
):
    db_path = _resolve_db_path(db, request)
    return {"items": list_templates(db_path, limit=limit)}


@admin_router.post("/templates")
def api_upsert_template(
    body: TemplateUpsertIn,
    request: Request,
    db: Optional[str] = None,
    _user=Depends(require_role("operator")),
):
    db_path = _resolve_db_path(db, request)
    tpl = ChatTemplate(
        template_key=body.template_key,
        language=body.language,
        body=body.body,
        status=body.status,
    )
    out = upsert_template(db_path, tpl)
    audit_event("chat_template_upsert", request=request, meta={"template_key": out.template_key})
    return out
