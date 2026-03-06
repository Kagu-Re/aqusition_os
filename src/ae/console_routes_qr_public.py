from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, ConfigDict

from .api_keys import resolve_tenant_for_public_request, ensure_api_key_or_401
from .console_support import _resolve_db_path, _coarse_ip_hint
from .public_guard import rate_limit_or_429
from .event_bus import EventBus
from . import repo

public_router = APIRouter()


class QrScanIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    attribution_id: str
    referrer: str | None = None
    user_agent: str | None = None
    meta: dict = {}


@public_router.post("/qr/scan")
def qr_scan(payload: QrScanIn, request: Request):
    """Public QR scan intake endpoint (v1).

    This is meant to be called from a landing page (JS) or a lightweight redirect service.
    We store only coarse identifiers and emit an operational event for timeline correlation.
    """
    rate_limit_or_429(request)
    resolve_tenant_for_public_request(request)
    ensure_api_key_or_401(request)
    db_path = _resolve_db_path(request.query_params.get("db"), request)

    a = repo.get_qr_attribution(db_path, payload.attribution_id)
    if not a:
        raise HTTPException(status_code=404, detail="qr_attribution_not_found")

    meta = {
        **(payload.meta or {}),
        "referrer": payload.referrer or request.headers.get("referer"),
        "user_agent": payload.user_agent or request.headers.get("user-agent"),
        "ip_hint": _coarse_ip_hint(request.client.host if request.client else ""),
    }

    repo.insert_qr_scan(db_path, attribution_id=payload.attribution_id, meta=meta)

    try:
        EventBus.emit_topic(
            db_path,
            topic="op.qr.scanned",
            aggregate_type="qr",
            aggregate_id=payload.attribution_id,
            payload={
                "attribution_id": payload.attribution_id,
                "kind": a.kind,
                "menu_id": a.menu_id,
                "url": a.url,
            },
        )
    except Exception:
        pass

    return {"status": "ok", "attribution_id": payload.attribution_id, "kind": a.kind, "menu_id": a.menu_id}
