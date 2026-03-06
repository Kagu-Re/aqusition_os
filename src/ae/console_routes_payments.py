from __future__ import annotations

from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .console_support import require_role, _resolve_db_path
from .audit import audit_event
from .tenant.context import get_scoped_client_id
from . import repo
from .enums import PaymentProvider, PaymentMethod, PaymentStatus, ReconciliationStatus


admin_router = APIRouter()


def _effective_client_id(request: Request) -> str | None:
    return get_scoped_client_id(request)


class PaymentCreateIn(BaseModel):
    payment_id: str = Field(min_length=1)
    booking_id: str = Field(min_length=1)
    lead_id: int
    amount: float = Field(ge=0)
    currency: str = Field(default="THB", min_length=1)
    provider: PaymentProvider = PaymentProvider.manual
    method: PaymentMethod = PaymentMethod.other
    status: PaymentStatus = PaymentStatus.pending
    external_ref: Optional[str] = None
    meta_json: Dict[str, Any] = Field(default_factory=dict)





class PaymentReconcileIn(BaseModel):
    status: ReconciliationStatus = ReconciliationStatus.unmatched
    matched_amount: Optional[float] = None
    matched_currency: Optional[str] = None
    matched_ref: Optional[str] = None
    note: Optional[str] = None
    updated_by: Optional[str] = None
    evidence_patch: Dict[str, Any] = Field(default_factory=dict)

class PaymentStatusIn(BaseModel):
    status: PaymentStatus
    external_ref: Optional[str] = None
    meta_patch: Dict[str, Any] = Field(default_factory=dict)


@admin_router.post("/api/payments")
def create_payment(payload: PaymentCreateIn, request: Request, _=Depends(require_role("operator"))):
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    p = repo.create_payment(
        db_path,
        payment_id=payload.payment_id,
        booking_id=payload.booking_id,
        lead_id=payload.lead_id,
        amount=payload.amount,
        currency=payload.currency,
        provider=payload.provider,
        method=payload.method,
        status=payload.status,
        external_ref=payload.external_ref,
        meta_json=payload.meta_json,
    )
    audit_event("payment_create", request, meta={"entity_type": "payment", "entity_id": p.payment_id, "booking_id": p.booking_id})
    return p


@admin_router.get("/api/payments")
def list_payments(
    request: Request,
    booking_id: Optional[str] = None,
    lead_id: Optional[int] = None,
    status: Optional[PaymentStatus] = None,
    limit: int = 200,
    _=Depends(require_role("operator")),
):
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    client_id = _effective_client_id(request)
    return repo.list_payments(db_path, booking_id=booking_id, lead_id=lead_id, status=status, client_id=client_id, limit=limit)


@admin_router.get("/api/payments/{payment_id}")
def get_payment(payment_id: str, request: Request, _=Depends(require_role("operator"))):
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    p = repo.get_payment(db_path, payment_id)
    if not p:
        return {"ok": False, "error": "not_found"}
    client_id = _effective_client_id(request)
    if client_id:
        lead = repo.get_lead(db_path, p.lead_id)
        if not lead or getattr(lead, "client_id", None) != client_id:
            raise HTTPException(status_code=403, detail="forbidden")
    return p


@admin_router.patch("/api/payments/{payment_id}/status")
def update_payment_status(payment_id: str, payload: PaymentStatusIn, request: Request, _=Depends(require_role("operator"))):
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    existing = repo.get_payment(db_path, payment_id)
    if existing:
        client_id = _effective_client_id(request)
        if client_id:
            lead = repo.get_lead(db_path, existing.lead_id)
            if not lead or getattr(lead, "client_id", None) != client_id:
                raise HTTPException(status_code=403, detail="forbidden")
    p = repo.update_payment_status(
        db_path,
        payment_id=payment_id,
        status=payload.status,
        external_ref=payload.external_ref,
        meta_patch=payload.meta_patch or {},
    )
    if not p:
        return {"ok": False, "error": "not_found"}
    audit_event("payment_status_update", request, meta={"entity_type": "payment", "entity_id": p.payment_id, "status": p.status.value})
    return p



@admin_router.get("/api/payments/reconciliation")
def list_reconciliation(
    request: Request,
    status: Optional[ReconciliationStatus] = None,
    limit: int = 200,
    _=Depends(require_role("operator")),
):
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    return repo.list_payments_reconciliation(db_path, status=status, limit=limit)


@admin_router.get("/api/payments/{payment_id}/reconciliation")
def get_reconciliation(payment_id: str, request: Request, _=Depends(require_role("operator"))):
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    rec = repo.get_payment_reconciliation(db_path, payment_id)
    if not rec:
        return {"ok": False, "error": "not_found"}
    return rec


@admin_router.put("/api/payments/{payment_id}/reconciliation")
def upsert_reconciliation(payment_id: str, payload: PaymentReconcileIn, request: Request, _=Depends(require_role("operator"))):
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    rec = repo.upsert_payment_reconciliation(
        db_path,
        payment_id=payment_id,
        status=payload.status,
        matched_amount=payload.matched_amount,
        matched_currency=payload.matched_currency,
        matched_ref=payload.matched_ref,
        note=payload.note,
        updated_by=payload.updated_by,
        evidence_patch=payload.evidence_patch or {},
    )
    audit_event(
        "payment_reconcile",
        request,
        meta={"entity_type": "payment", "entity_id": payment_id, "reconciliation_status": rec.status.value},
    )
    return rec
