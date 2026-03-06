from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from .auth import AuthUser
from . import repo
from .console_support import require_role, _resolve_db_path
from .tenant import get_scoped_client_id

router = APIRouter()

class SpendUpdateIn(BaseModel):
    day: Optional[str] = None
    source: Optional[str] = None
    utm_campaign: Optional[str] = None
    client_id: Optional[str] = None
    spend_value: Optional[float] = None
    spend_currency: Optional[str] = None

class SpendImportIn(BaseModel):
    items: list[dict]

@router.post("/api/spend/import")
def spend_import(payload: SpendImportIn, request: Request, db: str, _: AuthUser = Depends(require_role("operator"))):
    """Import ad spend items (manual). Items schema (minimal):
    - day: YYYY-MM-DD (required)
    - source: 'meta'|'google'|... (required)
    - spend_value: number (required)
    - spend_currency: string (optional, default THB)
    - utm_campaign: string (optional)
    - client_id: string (optional)
    """
    db_path = _resolve_db_path(db, request)
    scoped = get_scoped_client_id(request)
    imported = 0
    errors: list[dict] = []
    for i, it in enumerate(payload.items or []):
        try:
            day = str(it.get("day") or "").strip()
            source = str(it.get("source") or "").strip()
            spend_value = float(it.get("spend_value"))
            if not day or not source:
                raise ValueError("missing day/source")
            item_client_id = it.get("client_id")
            if scoped:
                if item_client_id and item_client_id != scoped:
                    raise ValueError(f"client_id must match tenant scope ({scoped})")
                item_client_id = scoped
            repo.upsert_spend_daily(
                db_path,
                day=day,
                source=source,
                spend_value=spend_value,
                spend_currency=str(it.get("spend_currency") or "THB"),
                utm_campaign=(it.get("utm_campaign") or None),
                client_id=(item_client_id or it.get("client_id") or None),
                meta_json={k: v for k, v in it.items() if k not in {"day","source","spend_value","spend_currency","utm_campaign","client_id"}},
            )
            imported += 1
        except Exception as e:
            errors.append({"index": i, "error": str(e), "item": it})
    try:
        repo.append_activity(
            db_path,
            entity_type="ad_spend_daily",
            entity_id="bulk",
            actor="operator",
            details={"imported": imported, "errors": errors[:10]},
        )
    except Exception:
        pass
    return {"ok": len(errors) == 0, "imported": imported, "errors": errors}

@router.post("/api/spend/{spend_id}")
def spend_update(spend_id: int, payload: SpendUpdateIn, request: Request, db: str, _: AuthUser = Depends(require_role("operator"))):
    db_path = _resolve_db_path(db, request)
    scoped = get_scoped_client_id(request)
    if scoped:
        existing_client = repo.get_spend_daily_client_id(db_path, spend_id)
        if existing_client and existing_client != scoped:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="forbidden: spend not in tenant scope")
    repo.update_spend_daily(
        db_path,
        spend_id,
        day=payload.day,
        source=payload.source,
        utm_campaign=payload.utm_campaign,
        client_id=payload.client_id,
        spend_value=payload.spend_value,
        spend_currency=payload.spend_currency,
    )
    try:
        repo.append_activity(
            db_path,
            entity_type="ad_spend_daily",
            entity_id=str(spend_id),
            actor="operator",
            details=payload.model_dump(),
        )
    except Exception:
        pass
    return {"ok": True, "spend_id": spend_id}

@router.delete("/api/spend/{spend_id}")
def spend_delete(spend_id: int, request: Request, db: str, _: AuthUser = Depends(require_role("admin"))):
    db_path = _resolve_db_path(db, request)
    scoped = get_scoped_client_id(request)
    if scoped:
        existing_client = repo.get_spend_daily_client_id(db_path, spend_id)
        if existing_client and existing_client != scoped:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="forbidden: spend not in tenant scope")
    repo.delete_spend_daily(db_path, spend_id)
    try:
        repo.append_activity(
            db_path,
            entity_type="ad_spend_daily",
            entity_id=str(spend_id),
            actor="operator",
            details={},
        )
    except Exception:
        pass
    return {"ok": True, "spend_id": spend_id}

@router.get("/api/spend")
def spend_list(
    request: Request,
    db: str,
    limit: int = 200,
    day_from: Optional[str] = None,
    day_to: Optional[str] = None,
    source: Optional[str] = None,
    utm_campaign: Optional[str] = None,
    client_id: Optional[str] = None,
    _: None = Depends(require_role("viewer")),
):
    scoped = get_scoped_client_id(request)
    effective_client_id = scoped if scoped else client_id
    db_path = _resolve_db_path(db, request)
    items = repo.list_spend_daily(
        db_path,
        limit=limit,
        day_from=day_from,
        day_to=day_to,
        source=source,
        utm_campaign=utm_campaign,
        client_id=effective_client_id,
    )
    return {"count": len(items), "items": items}

@router.get("/api/stats/campaign")
def stats_campaign(
    request: Request,
    db: str,
    days: int = 30,
    utm_campaign: Optional[str] = None,
    client_id: Optional[str] = None,
    day_from: Optional[str] = None,
    day_to: Optional[str] = None,
    min_spend: float = 0.0,
    sort_by: str = "roas",
    _: None = Depends(require_role("viewer")),
):
    scoped = get_scoped_client_id(request)
    effective_client_id = scoped if scoped else client_id
    if not day_from and not day_to and days:
        today = datetime.utcnow().date()
        day_to_val = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        day_from_val = (today - timedelta(days=days)).strftime("%Y-%m-%d")
    else:
        day_from_val = day_from
        day_to_val = day_to
    out = repo.campaign_stats(
        _resolve_db_path(db, request),
        day_from=day_from_val,
        day_to=day_to_val,
        min_spend=min_spend,
        sort_by=sort_by,
        client_id=effective_client_id,
    )
    if utm_campaign and out.get("campaigns"):
        out["campaigns"] = [c for c in out["campaigns"] if (c.get("campaign") or "") == utm_campaign]
    return out

@router.get("/api/stats/kpi")
def stats_kpi(
    request: Request,
    db: str,
    days: int = 30,
    client_id: Optional[str] = None,
    day_from: Optional[str] = None,
    day_to: Optional[str] = None,
    _: None = Depends(require_role("viewer")),
):
    scoped = get_scoped_client_id(request)
    effective_client_id = scoped if scoped else client_id
    if not day_from and not day_to and days:
        today = datetime.utcnow().date()
        day_to_val = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        day_from_val = (today - timedelta(days=days)).strftime("%Y-%m-%d")
    else:
        day_from_val = day_from
        day_to_val = day_to
    return repo.kpi_stats(
        _resolve_db_path(db, request),
        day_from=day_from_val,
        day_to=day_to_val,
        client_id=effective_client_id,
    )
