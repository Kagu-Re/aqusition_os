from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from .console_support import require_role, _resolve_db_path
from . import repo
from .jobs.hook_retry_worker import process_due


admin_router = APIRouter()


@admin_router.get("/api/retries/hooks", dependencies=[Depends(require_role("admin"))])
def list_hook_retries(request: Request, status: Optional[str] = None, limit: int = 100):
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    items = repo.list_hook_retries(db_path, status=status, limit=limit)
    return {"count": len(items), "items": items}


@admin_router.get("/api/retries/hooks/{retry_id}", dependencies=[Depends(require_role("admin"))])
def get_hook_retry(request: Request, retry_id: str):
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    r = repo.get_hook_retry(db_path, retry_id)
    if r is None:
        return {"error": "not_found", "retry_id": retry_id}
    return r


class RunDueIn(BaseModel):
    limit: int = Field(default=50, ge=1, le=500)


@admin_router.post("/api/retries/hooks/run", dependencies=[Depends(require_role("admin"))])
def run_due_hook_retries(request: Request, body: RunDueIn):
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    processed = process_due(db_path, limit=body.limit)
    return {"processed": processed}
