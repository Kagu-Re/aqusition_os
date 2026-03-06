from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict

from . import repo, service, models
from .console_support import require_role, _resolve_db, _resolve_db_path, _coarse_ip_hint
from .tenant import get_scoped_client_id
from .api_keys import resolve_tenant_for_public_request, ensure_api_key_or_401
from .public_guard import rate_limit_or_429
from .audit import audit_event

# Split routers to allow public API deployment separate from Operator Console.
public_router = APIRouter()
admin_router = APIRouter()

class LeadOutcomeIn(BaseModel):
    status: Optional[str] = None
    booking_status: Optional[str] = None
    booking_value: Optional[float] = None
    booking_currency: Optional[str] = None
    booking_ts: Optional[str] = None

class LeadIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    source: Optional[str] = None
    page_id: Optional[str] = None
    client_id: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    message: Optional[str] = None
    hp: Optional[str] = Field(default=None, alias="_hp")
    utm: dict = Field(default_factory=dict)

@public_router.post("/lead")
def lead_intake(payload: LeadIn, request: Request):
    """Public endpoint for website forms. Minimal, privacy-preserving.

    Notes:
    - We store only form fields + UTM + user-agent + coarse ip_hint (no raw IP).
    - Spam is filtered via small heuristic score; spam leads are stored but not notified.
    - When multi-tenant: X-Tenant-ID (or subdomain/path) sets client_id if not in payload.
    """
    rate_limit_or_429(request)
    resolve_tenant_for_public_request(request)
    ensure_api_key_or_401(request)
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    scoped = get_scoped_client_id(request)

    # Honeypot: bots often fill hidden fields
    if payload.hp and str(payload.hp).strip():
        import datetime as _dt
        try:
            repo.insert_abuse(
                db_path,
                ts=_dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                ip_hint=_coarse_ip_hint(request.client.host if request.client else ""),
                endpoint="/lead",
                reason="honeypot",
                meta={"len": len(str(payload.hp))},
            )
        except Exception:
            pass

        lead_id = repo.insert_lead(
            db_path,
            models.LeadIntake(
                ts=_dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                source=payload.source,
                page_id=payload.page_id,
                client_id=payload.client_id,
                name=(payload.name or "")[:80] if payload.name else None,
                phone=(payload.phone or "")[:32] if payload.phone else None,
                email=(payload.email or "")[:254] if payload.email else None,
                message=(payload.message or "")[:2000] if payload.message else None,
                utm_source=(payload.utm or {}).get("utm_source"),
                utm_medium=(payload.utm or {}).get("utm_medium"),
                utm_campaign=(payload.utm or {}).get("utm_campaign"),
                utm_term=(payload.utm or {}).get("utm_term"),
                utm_content=(payload.utm or {}).get("utm_content"),
                referrer=request.headers.get("referer"),
                user_agent=request.headers.get("user-agent"),
                ip_hint=_coarse_ip_hint(request.client.host if request.client else ""),
                spam_score=100,
                is_spam=1,
                status="spam",
                meta_json={"spam_reasons": ["honeypot"]},
            ),
        )
        audit_event("lead_intake", request, {"lead_id": lead_id, "spam": True, "reason": "honeypot"})
        return {"ok": True, "lead_id": lead_id, "spam": {"score": 100, "reasons": ["honeypot"]}}

    # Extract metadata
    ref = request.headers.get("referer")
    ua = request.headers.get("user-agent")

    # coarse ip hint: last octet removed if IPv4, otherwise empty
    ip = request.client.host if request.client else ""
    ip_hint = ""
    if ip and "." in ip:
        parts = ip.split(".")
        if len(parts) == 4:
            ip_hint = ".".join(parts[:3] + ["0"])

    effective_client_id = scoped if scoped else payload.client_id
    lead_id, spam = service.intake_lead(
        db_path,
        source=payload.source,
        page_id=payload.page_id,
        client_id=effective_client_id,
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        message=payload.message,
        utm=payload.utm,
        referrer=ref,
        user_agent=ua,
        ip_hint=ip_hint,
    )
    audit_event("lead_intake", request, {"lead_id": lead_id, "spam": bool((spam or {}).get("is_spam")), "score": (spam or {}).get("score")})
    return {"ok": True, "lead_id": lead_id, "spam": spam}

@admin_router.get("/api/leads")
def leads(
    request: Request,
    db: str,
    limit: int = 200,
    status: Optional[str] = None,
    is_spam: Optional[int] = None,
    client_id: Optional[str] = None,
    page_id: Optional[str] = None,
    _: None = Depends(require_role("viewer")),
):
    scoped = get_scoped_client_id(request)
    effective_client_id = scoped if scoped else client_id
    db_path = _resolve_db_path(db, request)
    items = repo.list_leads(db_path, limit=limit, status=status, is_spam=is_spam, client_id=effective_client_id, page_id=page_id)
    return {"count": len(items), "items": [it.model_dump() for it in items]}

@admin_router.post("/api/leads/{lead_id}/outcome")
def lead_outcome(
    lead_id: int,
    payload: LeadOutcomeIn,
    request: Request,
    db: str,
    _: None = Depends(require_role("viewer")),
):
    db_path = _resolve_db_path(db, request)
    scoped = get_scoped_client_id(request)
    if scoped:
        lead = repo.get_lead(db_path, lead_id)
        if lead and lead.client_id != scoped:
            raise HTTPException(status_code=403, detail="forbidden: lead not in tenant scope")
    service.set_lead_outcome(
        db_path,
        lead_id,
        status=payload.status,
        booking_status=payload.booking_status,
        booking_value=payload.booking_value,
        booking_currency=payload.booking_currency,
        booking_ts=payload.booking_ts,
        actor="operator",
    )
    audit_event("lead_outcome", None, {"lead_id": lead_id, "actor": "operator"})
    return {"ok": True, "lead_id": lead_id}
