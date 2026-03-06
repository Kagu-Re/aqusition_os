from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List

from .console_support import require_role, _resolve_db_path
from .tenant import get_scoped_client_id
from . import repo
from .models import ServicePackage
from .service_bulk_packages import run_bulk_update_packages, run_bulk_delete_packages
from datetime import datetime

admin_router = APIRouter(prefix="/api/service-packages", tags=["service-packages"])

_admin = require_role("operator")


class ServicePackageCreate(BaseModel):
    package_id: str = Field(min_length=1)
    client_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    price: float = Field(ge=0)
    duration_min: int = Field(ge=1)
    addons: List[str] = Field(default_factory=list)
    active: bool = True
    meta_json: dict = Field(default_factory=dict)


class ServicePackageUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0)
    duration_min: Optional[int] = Field(default=None, ge=1)
    addons: Optional[List[str]] = None
    active: Optional[bool] = None
    meta_json: Optional[dict] = None


@admin_router.get("")
def list_service_packages(
    request: Request,
    client_id: Optional[str] = None,
    active: Optional[bool] = None,
    limit: int = 50,
    _=Depends(_admin),
):
    """List service packages with optional filters."""
    scoped = get_scoped_client_id(request)
    effective_client_id = scoped if scoped else client_id
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    items = repo.list_packages(db_path, client_id=effective_client_id, active=active, limit=limit)
    return {"count": len(items), "items": [p.model_dump() for p in items]}


@admin_router.get("/{package_id}")
def get_service_package(package_id: str, request: Request, _=Depends(_admin)):
    """Get a service package by ID."""
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    pkg = repo.get_package(db_path, package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="package_not_found")
    scoped = get_scoped_client_id(request)
    if scoped and pkg.client_id != scoped:
        raise HTTPException(status_code=403, detail="forbidden: package not in tenant scope")
    return {"package": pkg.model_dump()}


@admin_router.post("")
def create_service_package(payload: ServicePackageCreate, request: Request, _=Depends(_admin)):
    """Create a new service package."""
    scoped = get_scoped_client_id(request)
    if scoped and payload.client_id != scoped:
        raise HTTPException(status_code=403, detail="forbidden: client_id must match tenant scope")
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    now = datetime.utcnow()
    package = ServicePackage(
        package_id=payload.package_id,
        client_id=payload.client_id,
        name=payload.name,
        price=payload.price,
        duration_min=payload.duration_min,
        addons=payload.addons or [],
        active=payload.active,
        meta_json=payload.meta_json or {},
        created_at=now,
        updated_at=now,
    )
    created = repo.create_package(db_path, package)
    return {"package": created.model_dump()}


@admin_router.put("/{package_id}")
def update_service_package(
    package_id: str,
    payload: ServicePackageUpdate,
    request: Request,
    _=Depends(_admin),
):
    """Update an existing service package."""
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    existing = repo.get_package(db_path, package_id)
    if not existing:
        raise HTTPException(status_code=404, detail="package_not_found")
    scoped = get_scoped_client_id(request)
    if scoped and existing.client_id != scoped:
        raise HTTPException(status_code=403, detail="forbidden: package not in tenant scope")

    # Merge updates
    updated = ServicePackage(
        package_id=package_id,
        client_id=existing.client_id,  # client_id cannot be changed
        name=payload.name if payload.name is not None else existing.name,
        price=payload.price if payload.price is not None else existing.price,
        duration_min=payload.duration_min if payload.duration_min is not None else existing.duration_min,
        addons=payload.addons if payload.addons is not None else existing.addons,
        active=payload.active if payload.active is not None else existing.active,
        meta_json=payload.meta_json if payload.meta_json is not None else existing.meta_json,
        created_at=existing.created_at,
        updated_at=datetime.utcnow(),
    )
    
    result = repo.update_package(db_path, updated)
    return {"package": result.model_dump()}


@admin_router.delete("/{package_id}")
def delete_service_package(
    package_id: str,
    request: Request,
    _=Depends(_admin),
):
    """Delete a service package."""
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    existing = repo.get_package(db_path, package_id)
    if not existing:
        raise HTTPException(status_code=404, detail="package_not_found")
    scoped = get_scoped_client_id(request)
    if scoped and existing.client_id != scoped:
        raise HTTPException(status_code=403, detail="forbidden: package not in tenant scope")

    repo.delete_package(db_path, package_id)
    return {"ok": True, "package_id": package_id}


class BulkUpdatePackagesIn(BaseModel):
    package_ids: Optional[List[str]] = None
    client_id: Optional[str] = None
    active: Optional[bool] = None
    limit: int = Field(default=200, ge=1, le=1000)
    mode: str = Field(default="dry_run", pattern="^(dry_run|execute)$")
    updates: dict = Field(..., description="Update fields: {'active': bool} or {'price': float} or both")
    notes: Optional[str] = None


class BulkDeletePackagesIn(BaseModel):
    package_ids: Optional[List[str]] = None
    client_id: Optional[str] = None
    active: Optional[bool] = None
    limit: int = Field(default=200, ge=1, le=1000)
    mode: str = Field(default="dry_run", pattern="^(dry_run|execute)$")
    notes: Optional[str] = None


@admin_router.post("/bulk-update")
def bulk_update_packages(
    payload: BulkUpdatePackagesIn,
    request: Request,
    _=Depends(_admin),
):
    """Bulk update service packages.
    
    Updates can include:
    - active: bool - Set active status
    - price: float - Set price
    
    Example:
    {
        "client_id": "client1",
        "updates": {"active": true},
        "mode": "dry_run"
    }
    """
    scoped = get_scoped_client_id(request)
    effective_client_id = scoped if scoped else payload.client_id
    db_path = _resolve_db_path(request.query_params.get("db"), request)

    try:
        op = run_bulk_update_packages(
            db_path=db_path,
            package_ids=payload.package_ids,
            client_id=effective_client_id,
            active=payload.active,
            limit=payload.limit,
            mode=payload.mode,
            updates=payload.updates,
            notes=payload.notes,
        )
        return {
            "ok": True,
            "bulk_id": op.bulk_id,
            "status": op.status,
            "action": op.action,
            "mode": op.mode,
            "result": op.result_json,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk update failed: {str(e)}")


@admin_router.post("/bulk-delete")
def bulk_delete_packages(
    payload: BulkDeletePackagesIn,
    request: Request,
    _=Depends(_admin),
):
    """Bulk delete service packages.
    
    Example:
    {
        "client_id": "client1",
        "active": false,
        "mode": "dry_run"
    }
    """
    scoped = get_scoped_client_id(request)
    effective_client_id = scoped if scoped else payload.client_id
    db_path = _resolve_db_path(request.query_params.get("db"), request)

    try:
        op = run_bulk_delete_packages(
            db_path=db_path,
            package_ids=payload.package_ids,
            client_id=effective_client_id,
            active=payload.active,
            limit=payload.limit,
            mode=payload.mode,
            notes=payload.notes,
        )
        return {
            "ok": True,
            "bulk_id": op.bulk_id,
            "status": op.status,
            "action": op.action,
            "mode": op.mode,
            "result": op.result_json,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk delete failed: {str(e)}")
