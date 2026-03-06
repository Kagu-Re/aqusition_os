from __future__ import annotations

from fastapi import APIRouter, Depends, Request, HTTPException

from . import repo
from .console_support import _resolve_db_path
from .console_support import require_role
from .tenant import get_scoped_client_id


router = APIRouter(tags=["onboarding"])


def _validate_client_scoped(request: Request, client_id: str) -> None:
    """Raise 403 if multi-tenant and client_id not in scope."""
    scoped = get_scoped_client_id(request)
    if scoped and client_id != scoped:
        raise HTTPException(status_code=403, detail="forbidden: client not in tenant scope")


@router.get("/api/onboarding/{client_id}")
def api_get_onboarding(
    client_id: str,
    request: Request,
    db_path: str | None = None,
    _: None = Depends(require_role("viewer")),
):
    _validate_client_scoped(request, client_id)
    db_path_val = _resolve_db_path(db_path or (request.query_params.get("db_path") if request else None), request)
    items = repo.list_onboarding_templates(db_path_val, client_id)
    return {"client_id": client_id, "items": items}


@router.post("/api/onboarding/{client_id}/ensure-defaults")
def api_ensure_defaults(
    client_id: str,
    request: Request,
    db_path: str | None = None,
    _: None = Depends(require_role("admin")),
):
    _validate_client_scoped(request, client_id)
    db_path_val = _resolve_db_path(db_path or (request.query_params.get("db_path") if request else None), request)
    items = repo.ensure_default_onboarding_templates(db_path_val, client_id)
    return {"client_id": client_id, "items": items}


@router.put("/api/onboarding/{client_id}/{template_key}")
def api_put_template(
    client_id: str,
    template_key: str,
    payload: dict,
    request: Request,
    db_path: str | None = None,
    _: None = Depends(require_role("admin")),
):
    _validate_client_scoped(request, client_id)
    db_path_val = _resolve_db_path(db_path or (request.query_params.get("db_path") if request else None), request)
    content = payload.get("content")
    if not isinstance(content, str):
        raise HTTPException(status_code=400, detail="content_required")
    repo.upsert_onboarding_template(db_path_val, client_id, template_key, content)
    return {"ok": True}
