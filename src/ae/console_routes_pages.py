from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from . import repo
from . import service
from .console_support import require_role, _resolve_db_path
from .tenant import get_scoped_client_id

router = APIRouter()


class PageCreateIn(BaseModel):
    page_id: str = Field(min_length=1)
    client_id: str = Field(min_length=1)
    template_id: str = Field(min_length=1)
    template_version: str = Field(default="1.0.0")
    page_slug: str = Field(min_length=1)
    page_url: str = Field(min_length=1)
    page_status: str = Field(default="draft")
    content_version: int = Field(default=1)
    service_focus: Optional[str] = None
    locale: str = Field(default="en-AU")

@router.get("/api/pages")
def list_pages(
    request: Request,
    db: str,
    page_status: Optional[str] = None,
    client_id: Optional[str] = None,
    template_id: Optional[str] = None,
    geo_city: Optional[str] = None,
    geo_country: Optional[str] = None,
    limit: int = 200,
    _: None = Depends(require_role("viewer")),
):
    scoped = get_scoped_client_id(request)
    effective_client_id = scoped if scoped else client_id
    db_path = _resolve_db_path(db, request)
    pages = repo.list_pages_filtered(
        db_path,
        page_status=page_status,
        client_id=effective_client_id,
        template_id=template_id,
        geo_city=geo_city,
        geo_country=geo_country,
        limit=limit,
    )
    return {"count": len(pages), "items": [p.model_dump() for p in pages]}

@router.post("/api/pages")
def create_page(
    payload: PageCreateIn,
    request: Request,
    db: str,
    _: None = Depends(require_role("editor")),
):
    """Create a new landing page."""
    scoped = get_scoped_client_id(request)
    if scoped and payload.client_id != scoped:
        raise HTTPException(status_code=403, detail="forbidden: client_id must match tenant scope")
    db_path = _resolve_db_path(db, request)
    from .models import Page, PageStatus

    # Check if page already exists
    existing = repo.get_page(db_path, payload.page_id)
    if existing:
        raise HTTPException(status_code=400, detail=f"Page already exists: {payload.page_id}")
    
    page = Page(
        page_id=payload.page_id,
        client_id=payload.client_id,
        template_id=payload.template_id,
        template_version=payload.template_version,
        page_slug=payload.page_slug,
        page_url=payload.page_url,
        page_status=PageStatus(payload.page_status),
        content_version=payload.content_version,
        service_focus=payload.service_focus,
        locale=payload.locale,
    )
    
    repo.upsert_page(db_path, page)
    created = repo.get_page(db_path, page.page_id)
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create page")
    return created.model_dump()

@router.get("/api/pages/{page_id}")
def get_page(
    page_id: str,
    request: Request,
    db: str,
    _: None = Depends(require_role("viewer")),
):
    """Get a single page by ID."""
    db_path = _resolve_db_path(db, request)
    page = repo.get_page(db_path, page_id)
    if not page:
        raise HTTPException(status_code=404, detail=f"Page not found: {page_id}")
    scoped = get_scoped_client_id(request)
    if scoped and page.client_id != scoped:
        raise HTTPException(status_code=403, detail="forbidden: page not in tenant scope")
    return page.model_dump()

@router.post("/api/pages/{page_id}/validate")
def validate_page_endpoint(
    page_id: str,
    request: Request,
    db: str,
    _: None = Depends(require_role("editor")),
):
    """Validate a page."""
    db_path = _resolve_db_path(db, request)
    scoped = get_scoped_client_id(request)
    if scoped:
        page = repo.get_page(db_path, page_id)
        if page and page.client_id != scoped:
            raise HTTPException(status_code=403, detail="forbidden: page not in tenant scope")
    ok, errors = service.validate_page(db_path, page_id)
    return {
        "ok": ok,
        "errors": errors,
        "page_id": page_id,
    }

@router.post("/api/pages/{page_id}/publish")
def publish_page_endpoint(
    page_id: str,
    request: Request,
    db: str,
    notes: Optional[str] = None,
    _: None = Depends(require_role("editor")),
):
    """Publish a page."""
    db_path = _resolve_db_path(db, request)
    scoped = get_scoped_client_id(request)
    if scoped:
        page = repo.get_page(db_path, page_id)
        if page and page.client_id != scoped:
            raise HTTPException(status_code=403, detail="forbidden: page not in tenant scope")
    ok, errors = service.publish_page(db_path, page_id, notes=notes)
    if not ok:
        raise HTTPException(status_code=400, detail={"errors": errors})
    return {
        "ok": True,
        "page_id": page_id,
        "status": "live",
    }

@router.post("/api/pages/{page_id}/pause")
def pause_page_endpoint(
    page_id: str,
    request: Request,
    db: str,
    _: None = Depends(require_role("editor")),
):
    """Pause a page."""
    db_path = _resolve_db_path(db, request)
    scoped = get_scoped_client_id(request)
    if scoped:
        page = repo.get_page(db_path, page_id)
        if page and page.client_id != scoped:
            raise HTTPException(status_code=403, detail="forbidden: page not in tenant scope")
    from .models import PageStatus
    repo.update_page_status(db_path, page_id, PageStatus.paused)
    return {
        "ok": True,
        "page_id": page_id,
        "status": "paused",
    }
