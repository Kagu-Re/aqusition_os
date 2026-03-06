from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request

from .console_support import require_role, _resolve_db_path
from .tenant.context import get_scoped_client_id
from . import repo

router = APIRouter()


def _effective_client_id(request: Request) -> str | None:
    return get_scoped_client_id(request)


@router.get("/api/events")
def list_events(
    request: Request,
    db: str,
    page_id: Optional[str] = None,
    limit: int = 200,
    _: None = Depends(require_role("viewer")),
):
    """List tracking events.
    
    Returns events from the events table (tracking events from pages).
    When multi-tenant, scoped by client_id via page join.
    """
    db_path = _resolve_db_path(db, request)
    client_id = _effective_client_id(request)
    events = repo.list_events(db_path, page_id=page_id if page_id else None, client_id=client_id)
    
    # Limit results
    if limit > 0:
        events = events[-limit:]  # Most recent N events
    
    return {
        "count": len(events),
        "items": [e.model_dump() for e in events]
    }
