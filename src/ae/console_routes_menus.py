from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from .console_support import require_role, _resolve_db_path
from .tenant import get_scoped_client_id
from . import repo
from .models import Menu, MenuSection, MenuItem
from .menu_static_pages import write_menu_page
from .qr_codes import generate_qr_png, batch_generate_qr_png, QrSpec
from .enums import MenuStatus
from .event_bus import EventBus
from datetime import datetime

router = APIRouter(prefix="/api/menus", tags=["menus"])

_admin = require_role("operator")


class MenuUpsert(BaseModel):
    menu_id: str
    client_id: str
    name: str
    language: str = "en"
    currency: str = "THB"
    status: MenuStatus = MenuStatus.draft
    meta: dict = {}


@router.get("")
def list_menus(request: Request, client_id: str | None = None, status: str | None = None, limit: int = 50, _=Depends(_admin)):
    scoped = get_scoped_client_id(request)
    effective_client_id = scoped if scoped else client_id
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    items = repo.list_menus(db_path, client_id=effective_client_id, status=status, limit=limit)
    return {"count": len(items), "items": [i.model_dump() for i in items]}


@router.get("/{menu_id}")
def get_menu(menu_id: str, request: Request, _=Depends(_admin)):
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    m = repo.get_menu(db_path, menu_id)
    if not m:
        raise HTTPException(status_code=404, detail="menu_not_found")
    scoped = get_scoped_client_id(request)
    if scoped and m.client_id != scoped:
        raise HTTPException(status_code=403, detail="forbidden: menu not in tenant scope")
    sections = repo.list_menu_sections(db_path, menu_id)
    items = repo.list_menu_items(db_path, menu_id)
    return {"menu": m.model_dump(), "sections": [s.model_dump() for s in sections], "items": [it.model_dump() for it in items]}


@router.post("")
def upsert_menu(payload: MenuUpsert, request: Request, _=Depends(_admin)):
    scoped = get_scoped_client_id(request)
    if scoped and payload.client_id != scoped:
        raise HTTPException(status_code=403, detail="forbidden: client_id must match tenant scope")
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    m = Menu(
        menu_id=payload.menu_id,
        client_id=payload.client_id,
        name=payload.name,
        language=payload.language,
        currency=payload.currency,
        status=payload.status,
        meta=payload.meta or {},
        created_at=now,
        updated_at=now,
    )
    saved = repo.upsert_menu(db_path, m)
    return {"menu": saved.model_dump()}


class SectionUpsert(BaseModel):
    section_id: str
    title: str
    sort_order: int = 0


@router.post("/{menu_id}/sections")
def upsert_section(menu_id: str, payload: SectionUpsert, request: Request, _=Depends(_admin)):
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    m = repo.get_menu(db_path, menu_id)
    if m:
        scoped = get_scoped_client_id(request)
        if scoped and m.client_id != scoped:
            raise HTTPException(status_code=403, detail="forbidden: menu not in tenant scope")
    sec = MenuSection(section_id=payload.section_id, menu_id=menu_id, title=payload.title, sort_order=payload.sort_order)
    repo.upsert_menu_section(db_path, sec)
    return {"section": sec.model_dump()}


class ItemUpsert(BaseModel):
    item_id: str
    section_id: str | None = None
    title: str
    description: str | None = None
    price: float | None = None
    currency: str | None = None
    is_available: bool = True
    sort_order: int = 0
    meta: dict = {}


@router.post("/{menu_id}/items")
def upsert_item(menu_id: str, payload: ItemUpsert, request: Request, _=Depends(_admin)):
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    m = repo.get_menu(db_path, menu_id)
    if m:
        scoped = get_scoped_client_id(request)
        if scoped and m.client_id != scoped:
            raise HTTPException(status_code=403, detail="forbidden: menu not in tenant scope")
    it = MenuItem(
        item_id=payload.item_id,
        menu_id=menu_id,
        section_id=payload.section_id,
        title=payload.title,
        description=payload.description,
        price=payload.price,
        currency=payload.currency,
        is_available=payload.is_available,
        sort_order=payload.sort_order,
        meta=payload.meta or {},
    )
    repo.upsert_menu_item(db_path, it)
    return {"item": it.model_dump()}


@router.post("/{menu_id}/generate")
def generate_menu_page(menu_id: str, request: Request, output_dir: str = "generated/menus", _=Depends(_admin)):
    """Generate a static HTML page for a menu.

    v1: writes a self-contained HTML file to output_dir and returns the path.
    """
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    m = repo.get_menu(db_path, menu_id)
    if not m:
        raise HTTPException(status_code=404, detail="menu_not_found")
    scoped = get_scoped_client_id(request)
    if scoped and m.client_id != scoped:
        raise HTTPException(status_code=403, detail="forbidden: menu not in tenant scope")
    sections = repo.list_menu_sections(db_path, menu_id)
    items = repo.list_menu_items(db_path, menu_id)
    path = write_menu_page(output_dir, m, sections, items)
    return {"menu_id": menu_id, "output_path": path}




def __with_aid(url: str, attribution_id: str) -> str:
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}aid={attribution_id}"


def __create_menu_attribution(db_path: str, menu_id: str, base_url: str, meta: dict) -> str:
    # Create mapping record for later scan correlation
    attribution_id = str(uuid4())
    final_url = __with_aid(base_url, attribution_id)
    repo.create_qr_attribution(
        db_path,
        kind="menu",
        menu_id=menu_id,
        url=final_url,
        meta={"base_url": base_url, **(meta or {})},
        attribution_id=attribution_id,
    )
    return attribution_id

class MenuQrRequest(BaseModel):
    url: str | None = None
    output_dir: str = "generated/qr"
    box_size: int = 10
    border: int = 4
    enable_attribution: bool = True
    attribution_meta: dict = {}


@router.post("/{menu_id}/qr")
def generate_menu_qr(menu_id: str, payload: MenuQrRequest, request: Request, _=Depends(_admin)):
    """Generate a QR code PNG for a menu.

    url resolution order:
      1) payload.url
      2) menu.meta['public_url'] (if present)
      3) menu.meta['url'] (if present)
    """
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    m = repo.get_menu(db_path, menu_id)
    if not m:
        raise HTTPException(status_code=404, detail="menu_not_found")
    scoped = get_scoped_client_id(request)
    if scoped and m.client_id != scoped:
        raise HTTPException(status_code=403, detail="forbidden: menu not in tenant scope")
    url = payload.url or (m.meta or {}).get("public_url") or (m.meta or {}).get("url")
    if not url:
        raise HTTPException(status_code=400, detail="menu_url_required")
    attribution_id = None
    qr_url = url
    if payload.enable_attribution:
        attribution_id = __create_menu_attribution(db_path, menu_id, url, payload.attribution_meta or {})
        qr_url = __with_aid(url, attribution_id)
    out_path = generate_qr_png(qr_url, f"{payload.output_dir}/menu-{menu_id}.png", box_size=payload.box_size, border=payload.border)

    if attribution_id:
        # Emit op event for audit / timeline
        try:
            EventBus.emit_topic(
                db_path,
                topic="op.qr.generated",
                aggregate_type="qr",
                aggregate_id=attribution_id,
                payload={"attribution_id": attribution_id, "kind": "menu", "menu_id": menu_id, "url": qr_url, "output_path": out_path},
            )
        except Exception:
            pass

    return {"menu_id": menu_id, "url": qr_url, "output_path": out_path, "attribution_id": attribution_id}


class MenuQrBatchRequest(BaseModel):
    menu_ids: list[str]
    base_url: str
    output_dir: str = "generated/qr"
    box_size: int = 10
    border: int = 4
    enable_attribution: bool = True
    attribution_meta: dict = {}


@router.post("/qr/batch")
def generate_menu_qr_batch(payload: MenuQrBatchRequest, request: Request, _=Depends(_admin)):
    """Batch-generate QR codes for multiple menus.

    v1: assumes the menu page URL is base_url + '/menu-{menu_id}.html'.
    """
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    scoped = get_scoped_client_id(request)
    menu_ids = payload.menu_ids
    if scoped:
        menu_ids = [mid for mid in payload.menu_ids if (m := repo.get_menu(db_path, mid)) and m.client_id == scoped]
    base = payload.base_url.rstrip("/")
    items = []
    specs = []
    for mid in menu_ids:
        url = f"{base}/menu-{mid}.html"
        attribution_id = None
        qr_url = url
        if payload.enable_attribution:
            attribution_id = __create_menu_attribution(db_path, mid, url, payload.attribution_meta or {})
            qr_url = __with_aid(url, attribution_id)
        specs.append(QrSpec(key=f"menu-{mid}", data=qr_url))
        items.append({"menu_id": mid, "url": qr_url, "attribution_id": attribution_id})

    mapping = batch_generate_qr_png(specs, payload.output_dir, box_size=payload.box_size, border=payload.border)

    out_items = []
    for it in items:
        key = f"menu-{it['menu_id']}"
        out_path = mapping.get(key)
        rec = {**it, "key": key, "output_path": out_path}
        out_items.append(rec)
        if it.get("attribution_id"):
            try:
                EventBus.emit_topic(
                    db_path,
                    topic="op.qr.generated",
                    aggregate_type="qr",
                    aggregate_id=it["attribution_id"],
                    payload={"attribution_id": it["attribution_id"], "kind": "menu", "menu_id": it["menu_id"], "url": it["url"], "output_path": out_path},
                )
            except Exception:
                pass

    return {"count": len(out_items), "items": out_items}
