from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any

from .console_support import require_role, AuthUser
from . import service
from .models import PageStatus

router = APIRouter(prefix="/api/bulk", tags=["bulk"])

_admin = require_role("operator")


class BulkRunIn(BaseModel):
    action: Literal["validate", "pause", "publish"]
    db: str
    # selectors
    page_ids: Optional[list[str]] = None
    page_status: Optional[str] = None
    client_id: Optional[str] = None
    template_id: Optional[str] = None
    geo_city: Optional[str] = None
    geo_country: Optional[str] = None
    limit: int = 200

    # execution flags
    execute: bool = False
    force: bool = False  # publish only
    notes: Optional[str] = None
    adapter_override: Optional[dict[str, Any]] = None  # publish only


@router.post("/run")
def bulk_run(payload: BulkRunIn, _: AuthUser = Depends(_admin)):
    """Run bulk operations (validate, pause, or publish) on pages."""
    act = payload.action
    ids = payload.page_ids
    if act == "validate":
        op = service.run_bulk_validate(
            payload.db,
            page_ids=ids,
            page_status=payload.page_status,
            client_id=payload.client_id,
            template_id=payload.template_id,
            geo_city=payload.geo_city,
            geo_country=payload.geo_country,
            limit=payload.limit,
            mode="dry_run",
            notes=payload.notes,
        )
        return op.model_dump()

    if act == "pause":
        mode = "execute" if payload.execute else "dry_run"
        op = service.run_bulk_pause(
            payload.db,
            page_ids=ids,
            page_status=payload.page_status,
            client_id=payload.client_id,
            template_id=payload.template_id,
            geo_city=payload.geo_city,
            geo_country=payload.geo_country,
            limit=payload.limit,
            mode=mode,
            notes=payload.notes,
        )
        return op.model_dump()

    if act == "publish":
        mode = "execute" if payload.execute else "dry_run"
        op = service.run_bulk_publish(
            payload.db,
            page_ids=ids,
            page_status=payload.page_status or PageStatus.draft,
            client_id=payload.client_id,
            template_id=payload.template_id,
            geo_city=payload.geo_city,
            geo_country=payload.geo_country,
            limit=payload.limit,
            mode=mode,
            force=payload.force,
            notes=payload.notes,
            adapter_config_override=payload.adapter_override,
        )
        return op.model_dump()

    raise HTTPException(status_code=400, detail="unsupported_action")
