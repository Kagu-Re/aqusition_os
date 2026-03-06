from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional

from .console_support import require_role, _resolve_db_path
from .tenant import get_scoped_client_id
from . import repo
from .models import PaymentIntent
from datetime import datetime

admin_router = APIRouter(prefix="/api/payment-intents", tags=["payment-intents"])

_admin = require_role("operator")


class PaymentIntentCreate(BaseModel):
    intent_id: str = Field(min_length=1)
    lead_id: int
    booking_request_id: str = Field(min_length=1)
    amount: float = Field(ge=0)
    method: str  # "promptpay" | "stripe" | "bank"
    payment_link: Optional[str] = None
    meta_json: dict = Field(default_factory=dict)


@admin_router.get("")
def list_payment_intents_endpoint(
    request: Request,
    booking_request_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    _=Depends(_admin),
):
    """List payment intents with optional filters."""
    scoped = get_scoped_client_id(request)
    effective_client_id = scoped
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    items = repo.list_payment_intents(
        db_path,
        booking_request_id=booking_request_id,
        status=status,
        client_id=effective_client_id,
        limit=limit,
    )
    return {"count": len(items), "items": [i.model_dump() for i in items]}


@admin_router.get("/{intent_id}")
def get_payment_intent_endpoint(intent_id: str, request: Request, _=Depends(_admin)):
    """Get a payment intent by ID."""
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    intent = repo.get_payment_intent(db_path, intent_id)
    if not intent:
        raise HTTPException(status_code=404, detail="payment_intent_not_found")
    scoped = get_scoped_client_id(request)
    if scoped:
        pi_client = repo.get_payment_intent_client_id(db_path, intent_id)
        if pi_client and pi_client != scoped:
            raise HTTPException(status_code=403, detail="forbidden: payment intent not in tenant scope")
    return {"intent": intent.model_dump()}


@admin_router.post("")
def create_payment_intent_endpoint(payload: PaymentIntentCreate, request: Request, _=Depends(_admin)):
    """Create a new payment intent."""
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    scoped = get_scoped_client_id(request)
    if scoped:
        lead = repo.get_lead(db_path, payload.lead_id)
        if lead and lead.client_id and lead.client_id != scoped:
            raise HTTPException(status_code=403, detail="forbidden: lead not in tenant scope")
    now = datetime.utcnow()
    intent = PaymentIntent(
        intent_id=payload.intent_id,
        lead_id=payload.lead_id,
        booking_request_id=payload.booking_request_id,
        amount=payload.amount,
        method=payload.method,
        status="requested",
        payment_link=payload.payment_link,
        meta_json=payload.meta_json or {},
        created_at=now,
        updated_at=now,
    )
    created = repo.create_payment_intent(db_path, intent)
    return {"intent": created.model_dump()}


@admin_router.put("/{intent_id}/mark-paid")
def mark_payment_intent_paid_endpoint(intent_id: str, request: Request, _=Depends(_admin)):
    """Mark payment intent as paid (creates Payment and updates BookingRequest)."""
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    scoped = get_scoped_client_id(request)
    if scoped:
        pi_client = repo.get_payment_intent_client_id(db_path, intent_id)
        if pi_client and pi_client != scoped:
            raise HTTPException(status_code=403, detail="forbidden: payment intent not in tenant scope")
    updated = repo.mark_payment_intent_paid(db_path, intent_id)
    if not updated:
        raise HTTPException(status_code=404, detail="payment_intent_not_found")
    return {"intent": updated.model_dump()}
