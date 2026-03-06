from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional

from .console_support import require_role, _resolve_db_path
from .tenant import get_scoped_client_id
from . import repo
from . import service
from . import reporting

router = APIRouter(prefix="/api", tags=["analytics"])

_viewer = require_role("viewer")


@router.get("/sim/budget")
def sim_budget(
    request: Request,
    db: str,
    campaign: str,
    delta_spend: float,
    mode: str = "roas_const",
    day_from: Optional[str] = None,
    day_to: Optional[str] = None,
    client_id: Optional[str] = None,
    _: None = Depends(_viewer),
):
    """Simulate budget changes and project impact."""
    scoped = get_scoped_client_id(request)
    effective_client_id = scoped if scoped else client_id
    return repo.simulate_budget(
        _resolve_db_path(db, request),
        campaign=campaign,
        delta_spend=delta_spend,
        mode=mode,
        day_from=day_from,
        day_to=day_to,
        client_id=effective_client_id,
    )


@router.get("/kpi/page/{page_id}")
def kpi_report_page(
    request: Request,
    page_id: str,
    db: str,
    since_iso: Optional[str] = None,
    until_iso: Optional[str] = None,
    platform: Optional[str] = None,
    _: None = Depends(_viewer),
):
    """Get KPI report for a specific page."""
    db_path = _resolve_db_path(db, request)
    result = service.kpi_report(
        db_path,
        page_id=page_id,
        since_iso=since_iso,
        platform=platform,
    )
    return result


@router.get("/kpi/client/{client_id}")
def kpi_report_client(
    request: Request,
    client_id: str,
    db: str,
    since_iso: Optional[str] = None,
    until_iso: Optional[str] = None,
    platform: Optional[str] = None,
    _: None = Depends(_viewer),
):
    """Get KPI report for a client (aggregated across pages)."""
    scoped = get_scoped_client_id(request)
    if scoped and client_id != scoped:
        raise HTTPException(status_code=403, detail="forbidden: client not in tenant scope")
    db_path = _resolve_db_path(db, request)
    result = reporting.kpi_report_for_client(
        db_path,
        client_id=client_id,
        platform=platform,
        since_iso=since_iso,
    )
    return result
