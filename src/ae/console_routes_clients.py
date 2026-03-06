from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from typing import Optional

from . import repo
from .console_support import require_secret, _resolve_db_path
from .tenant import get_scoped_client_id
from . import db as dbmod

router = APIRouter()

@router.get("/api/clients")
def api_clients(
    request: Request,
    db_path: str | None = None,
    status: str | None = None,
    limit: int = 200,
):
    require_secret(request)
    db_path = _resolve_db_path(db_path, request)
    dbmod.init_db(db_path)
    scoped = get_scoped_client_id(request)
    if scoped:
        # Multi-tenant: return only the scoped client
        c = repo.get_client(db_path, scoped)
        clients = [c] if c else []
    else:
        clients = repo.list_clients(db_path, status=status, limit=limit)
    return {"clients": [c.model_dump() if hasattr(c, "model_dump") else c.dict() for c in clients]}


@router.get("/api/clients/{client_id}")
def api_get_client(
    request: Request,
    client_id: str,
    db_path: str | None = None,
):
    """Get a single client by ID."""
    require_secret(request)
    scoped = get_scoped_client_id(request)
    if scoped and client_id != scoped:
        raise HTTPException(status_code=403, detail="forbidden: client not in tenant scope")
    db_path = _resolve_db_path(db_path, request)
    dbmod.init_db(db_path)
    client = repo.get_client(db_path, client_id=client_id)
    if not client:
        raise HTTPException(status_code=404, detail="client_not_found")
    return client.model_dump() if hasattr(client, "model_dump") else client.dict()

@router.post("/api/clients")
def api_upsert_client(
    request: Request,
    payload: dict,
    db_path: str | None = None,
):
    require_secret(request)
    scoped = get_scoped_client_id(request)
    db_path = _resolve_db_path(db_path, request)
    dbmod.init_db(db_path)

    from ae.models import Client

    client_id = (payload.get("client_id") or payload.get("slug") or "").strip().lower()
    if scoped and client_id != scoped:
        raise HTTPException(status_code=403, detail="forbidden: client_id must match tenant scope")
    client_name = (payload.get("client_name") or payload.get("name") or "").strip()
    trade = (payload.get("trade") or payload.get("industry") or "").strip().lower()
    business_model = (payload.get("business_model") or "quote_based").strip().lower()
    geo_country = (payload.get("geo_country") or "TH").strip().upper()
    geo_city = (payload.get("geo_city") or payload.get("geo") or "").strip().lower()
    service_area = payload.get("service_area") or [geo_city]
    primary_phone = (payload.get("primary_phone") or "").strip()
    lead_email = (payload.get("lead_email") or payload.get("owner_email") or "").strip()
    status = (payload.get("status") or "draft").strip().lower()
    hours = payload.get("hours")
    license_badges = payload.get("license_badges") or []
    price_anchor = payload.get("price_anchor")
    brand_theme = payload.get("brand_theme")
    notes_internal = payload.get("notes_internal") or payload.get("offer") or payload.get("notes")
    service_config_json = payload.get("service_config_json") or {}
    
    # Allow skipping auto-population of defaults
    apply_defaults = payload.get("apply_defaults", True)
    if isinstance(apply_defaults, str):
        apply_defaults = apply_defaults.lower() not in ("false", "0", "no", "skip")

    if not client_id or not client_name or not trade or not geo_city or not primary_phone or not lead_email:
        raise HTTPException(
            status_code=400,
            detail="required: client_id/slug, client_name/name, trade/industry, geo_city/geo, primary_phone, lead_email",
        )

    try:
        from ae.enums import BusinessModel, Trade, ClientStatus
        c = Client(
            client_id=client_id,
            client_name=client_name,
            trade=Trade(trade) if isinstance(trade, str) else trade,
            business_model=BusinessModel(business_model) if business_model else BusinessModel.quote_based,
            geo_country=geo_country,
            geo_city=geo_city,
            service_area=service_area,
            primary_phone=primary_phone,
            lead_email=lead_email,
            status=ClientStatus(status) if isinstance(status, str) else status,
            hours=hours,
            license_badges=license_badges,
            price_anchor=price_anchor,
            brand_theme=brand_theme,
            notes_internal=notes_internal,
            service_config_json=service_config_json,
        )
        # Upsert with auto-population (defaults to True)
        repo.upsert_client(db_path, c, apply_defaults=apply_defaults)
        stored = repo.get_client(db_path, client_id=client_id)
        return {"client": stored.model_dump() if hasattr(stored, "model_dump") else stored.dict()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/clients/{client_id}/reapply-template")
def api_reapply_template(
    request: Request,
    client_id: str,
    payload: dict,
    db_path: str | None = None,
):
    """Reapply trade template defaults to an existing client."""
    require_secret(request)
    scoped = get_scoped_client_id(request)
    if scoped and client_id != scoped:
        raise HTTPException(status_code=403, detail="forbidden: client not in tenant scope")
    db_path = _resolve_db_path(db_path, request)
    dbmod.init_db(db_path)
    client = repo.get_client(db_path, client_id=client_id)
    if not client:
        raise HTTPException(status_code=404, detail="client_not_found")
    create_packages = payload.get("create_packages", False)
    if isinstance(create_packages, str):
        create_packages = create_packages.lower() in ("true", "1", "yes")

    from ae.client_service import (
        apply_trade_template_to_client,
        generate_default_service_config,
        create_default_packages_from_template,
    )

    client = apply_trade_template_to_client(client, overwrite=True)
    client.service_config_json = generate_default_service_config(client, overwrite=True)
    repo.upsert_client(db_path, client, apply_defaults=False)
    if create_packages:
        create_default_packages_from_template(db_path, client)
    stored = repo.get_client(db_path, client_id=client_id)
    return {"client": stored.model_dump() if hasattr(stored, "model_dump") else stored.dict()}


@router.post("/api/clients/{client_id}/sync-packages-from-template")
def api_sync_packages_from_template(
    request: Request,
    client_id: str,
    payload: dict,
    db_path: str | None = None,
):
    """Sync service packages from trade template. merge by default; overwrite to replace all."""
    require_secret(request)
    scoped = get_scoped_client_id(request)
    if scoped and client_id != scoped:
        raise HTTPException(status_code=403, detail="forbidden: client not in tenant scope")
    db_path = _resolve_db_path(db_path, request)
    dbmod.init_db(db_path)
    client = repo.get_client(db_path, client_id=client_id)
    if not client:
        raise HTTPException(status_code=404, detail="client_not_found")
    overwrite = payload.get("overwrite", False)
    if isinstance(overwrite, str):
        overwrite = overwrite.lower() in ("true", "1", "yes")

    from ae.client_service import sync_packages_from_template

    try:
        packages = sync_packages_from_template(db_path, client_id, overwrite=overwrite)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"created": len(packages), "packages": [p.model_dump() for p in packages]}


@router.post("/api/clients/{client_id}/status")
def api_set_client_status(
    request: Request,
    client_id: str,
    payload: dict,
    db_path: str | None = None,
):
    require_secret(request)
    scoped = get_scoped_client_id(request)
    if scoped and client_id != scoped:
        raise HTTPException(status_code=403, detail="forbidden: client not in tenant scope")
    db_path = _resolve_db_path(db_path, request)
    dbmod.init_db(db_path)
    status = (payload.get("status") or "").strip().lower()
    try:
        c = repo.set_client_status(db_path, client_id=client_id, status=status)
        return {"client": c.model_dump() if hasattr(c, "model_dump") else c.dict()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
