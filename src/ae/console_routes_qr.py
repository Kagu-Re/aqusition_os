from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from .console_support import require_role, _resolve_db_path
from .tenant.context import get_scoped_client_id
from . import repo

router = APIRouter(prefix="/api/qr", tags=["qr"])
_admin = require_role("operator")


def _effective_client_id(request: Request) -> str | None:
    return get_scoped_client_id(request)


@router.get("/attributions")
def list_attributions(request: Request, menu_id: str | None = None, limit: int = 50, _=Depends(_admin)):
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    client_id = _effective_client_id(request)
    items = repo.list_qr_attributions(db_path, menu_id=menu_id, client_id=client_id, limit=limit)
    return {"count": len(items), "items": [i.model_dump() for i in items]}


@router.get("/attributions/{attribution_id}")
def get_attribution(attribution_id: str, request: Request, _=Depends(_admin)):
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    a = repo.get_qr_attribution(db_path, attribution_id)
    if not a:
        raise HTTPException(status_code=404, detail="qr_attribution_not_found")
    client_id = _effective_client_id(request)
    if client_id:
        if not a.menu_id:
            raise HTTPException(status_code=403, detail="forbidden")
        menu = repo.get_menu(db_path, a.menu_id)
        if not menu or getattr(menu, "client_id", None) != client_id:
            raise HTTPException(status_code=403, detail="forbidden")
    scans = repo.list_qr_scans(db_path, attribution_id=attribution_id, limit=50)
    return {"attribution": a.model_dump(), "scan_count": len(scans)}


class ScanListRequest(BaseModel):
    attribution_id: str
    limit: int = 50


@router.post("/scans")
def list_scans(payload: ScanListRequest, request: Request, _=Depends(_admin)):
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    scans = repo.list_qr_scans(db_path, attribution_id=payload.attribution_id, limit=payload.limit)
    return {"count": len(scans), "items": [s.model_dump() for s in scans]}
