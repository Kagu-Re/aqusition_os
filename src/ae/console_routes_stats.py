from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from typing import Optional

from .console_support import require_role, _resolve_db_path
from .tenant import get_scoped_client_id
from . import repo

router = APIRouter(prefix="/api/stats", tags=["stats"])

_viewer = require_role("viewer")


@router.get("/campaigns")
def stats_campaigns(
    request: Request,
    db: str,
    day_from: Optional[str] = None,
    day_to: Optional[str] = None,
    min_spend: float = 0.0,
    sort_by: str = "roas",
    client_id: Optional[str] = None,
    _: None = Depends(_viewer),
):
    """Get campaign statistics."""
    scoped = get_scoped_client_id(request)
    effective_client_id = scoped if scoped else client_id
    return repo.campaign_stats(
        _resolve_db_path(db, request),
        day_from=day_from,
        day_to=day_to,
        min_spend=min_spend,
        sort_by=sort_by,
        client_id=effective_client_id,
    )


@router.get("/kpis")
def stats_kpis(
    request: Request,
    db: str,
    day_from: Optional[str] = None,
    day_to: Optional[str] = None,
    client_id: Optional[str] = None,
    _: None = Depends(_viewer),
):
    """Get KPI statistics."""
    scoped = get_scoped_client_id(request)
    effective_client_id = scoped if scoped else client_id
    return repo.kpi_stats(
        _resolve_db_path(db, request),
        day_from=day_from,
        day_to=day_to,
        client_id=effective_client_id,
    )


@router.get("/roas")
def stats_roas(
    request: Request,
    db: str,
    client_id: Optional[str] = None,
    _: None = Depends(_viewer),
):
    """Get ROAS statistics."""
    scoped = get_scoped_client_id(request)
    effective_client_id = scoped if scoped else client_id
    return repo.roas_stats(_resolve_db_path(db, request), client_id=effective_client_id)


@router.get("/revenue")
def stats_revenue(
    request: Request,
    db: str,
    client_id: Optional[str] = None,
    _: None = Depends(_viewer),
):
    """Get revenue statistics."""
    scoped = get_scoped_client_id(request)
    effective_client_id = scoped if scoped else client_id
    return repo.revenue_stats(_resolve_db_path(db, request), client_id=effective_client_id)
