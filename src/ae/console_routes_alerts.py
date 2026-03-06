from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional

from .console_support import require_role, _resolve_db_path
from . import repo

router = APIRouter(prefix="/api", tags=["alerts"])

_admin = require_role("operator")
_viewer = require_role("viewer")


@router.get("/alerts/thresholds")
def alerts_get_thresholds(
    request: Request,
    db: str,
    _: None = Depends(_viewer),
):
    """Get alert thresholds configuration."""
    return repo.get_thresholds(_resolve_db_path(db, request))


@router.put("/alerts/thresholds")
def alerts_set_thresholds(
    request: Request,
    db: str,
    body: dict,
    _: None = Depends(_viewer),
):
    """Set alert thresholds configuration."""
    return repo.set_thresholds(_resolve_db_path(db, request), body)


@router.post("/alerts/evaluate")
def alerts_evaluate(
    request: Request,
    db: str,
    day_from: Optional[str] = None,
    day_to: Optional[str] = None,
    notify: bool = False,
    _: None = Depends(_viewer),
):
    """Evaluate alerts for a given date range."""
    db_path = _resolve_db_path(db, request)
    out = repo.evaluate_alerts(db_path, day_from=day_from, day_to=day_to)
    if notify:
        out["notify"] = repo.notify_alerts(db_path, out.get("created_alerts") or [])
    return out


@router.get("/notify/config")
def notify_get_config(
    request: Request,
    db: str,
    _: None = Depends(_viewer),
):
    """Get notification configuration."""
    return repo.get_notify_config(_resolve_db_path(db, request))


@router.put("/notify/config")
def notify_set_config(
    request: Request,
    db: str,
    body: dict,
    _: None = Depends(_viewer),
):
    """Set notification configuration."""
    return repo.set_notify_config(_resolve_db_path(db, request), body)


@router.post("/notify/test")
def notify_test(
    request: Request,
    db: str,
    _: None = Depends(_viewer),
):
    """Test notification configuration."""
    return repo.test_notify(_resolve_db_path(db, request))


@router.get("/playbooks")
def playbooks_list(
    _: None = Depends(_viewer),
):
    """List all playbooks."""
    return repo.list_playbooks()


@router.post("/alerts/ack")
def alerts_ack(
    request: Request,
    db: str,
    body: dict,
    _: None = Depends(_viewer),
):
    """Acknowledge an alert."""
    alert_id = int(body.get("id"))
    note = str(body.get("note") or "")
    who = str(body.get("by") or "operator")
    return repo.ack_alert(_resolve_db_path(db, request), alert_id, ack_by=who, note=note)


@router.post("/alerts/resolve")
def alerts_resolve(
    request: Request,
    db: str,
    body: dict,
    _: None = Depends(_viewer),
):
    """Resolve an alert."""
    alert_id = int(body.get("id"))
    note = str(body.get("note") or "")
    who = str(body.get("by") or "operator")
    return repo.resolve_alert(_resolve_db_path(db, request), alert_id, ack_by=who, note=note)


@router.get("/alerts/list")
def alerts_list(
    request: Request,
    db: str,
    status: Optional[str] = None,
    limit: int = 200,
    _: None = Depends(_viewer),
):
    """List alerts with optional status filter."""
    return repo.list_alerts(_resolve_db_path(db, request), status=status, limit=limit)
