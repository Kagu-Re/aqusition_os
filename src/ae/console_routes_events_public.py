from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

from .api_keys import resolve_tenant_for_public_request, ensure_api_key_or_401
from .console_support import _resolve_db_path
from .public_guard import rate_limit_or_429
from . import repo
from . import service
from .enums import EventName

public_router = APIRouter()

class EventIn(BaseModel):
    page_id: str
    event_name: str
    params: Optional[Dict[str, Any]] = None

@public_router.post("/event")
def record_event_public(payload: EventIn, request: Request):
    """Public endpoint for recording events from web pages.
    
    This allows HTML pages to send tracking events to the database.
    Used for validation and analytics.
    """
    rate_limit_or_429(request)
    resolve_tenant_for_public_request(request)
    ensure_api_key_or_401(request)
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    
    # Validate event name
    try:
        event_name_enum = EventName(payload.event_name)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid event_name: {payload.event_name}. Must be one of: call_click, quote_submit, thank_you_view, package_selected")
    
    # Record event
    try:
        ev = service.record_event(
            db_path=db_path,
            page_id=payload.page_id,
            event_name=event_name_enum,
            params=payload.params or {}
        )
        return {
            "status": "ok",
            "event_id": ev.event_id,
            "event_name": ev.event_name.value,
            "page_id": ev.page_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record event: {str(e)}")
