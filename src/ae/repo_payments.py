from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import TypeAdapter

from .db import connect, init_db
from .models import Payment, PaymentReconciliation
from .enums import PaymentStatus, PaymentProvider, PaymentMethod, ReconciliationStatus
from .payment_registry import validate_payment_provider_method, validate_external_ref

from .event_bus import EventBus
from .repo_states import get_state


def _dt(v: str) -> datetime:
    return datetime.fromisoformat(v)



def _ensure_reconciliation_default(db_path: str, *, payment_id: str, currency: str, amount: float) -> None:
    """Ensure a default reconciliation record exists (status=unmatched).

    Safe to call repeatedly.
    """
    init_db(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT payment_id FROM payment_reconciliation WHERE payment_id = ?",
            (payment_id,),
        ).fetchone()
        if row:
            return

    now = datetime.utcnow()
    evidence = {"expected_amount": float(amount), "expected_currency": currency}
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO payment_reconciliation (
                payment_id, status, matched_amount, matched_currency, matched_ref,
                note, updated_by, created_at, updated_at, evidence_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payment_id,
                ReconciliationStatus.unmatched.value,
                None,
                currency,
                None,
                None,
                None,
                now.isoformat(),
                now.isoformat(),
                json.dumps(evidence, ensure_ascii=False),
            ),
        )



class PaymentBindingError(ValueError):
    """Raised when payment does not bind cleanly to a booking/lead."""


def _expected_booking_id_for_lead(lead_id: int) -> str:
    return f"lead-{int(lead_id)}"


def _validate_payment_booking_binding(
    db_path: str,
    *,
    booking_id: str,
    lead_id: int,
    amount: float,
    currency: str,
) -> None:
    """Enforce Payment → Booking binding invariants.

    v1 invariants:
    - lead must exist
    - booking_id must equal f"lead-{lead_id}"
    - lead must have non-empty booking_status and must not be cancelled
    - if lead has booking_currency, payment currency must match
    - if lead has booking_value > 0, payment amount must be <= booking_value
    """
    from .repo_leads import get_lead

    lead = get_lead(db_path, int(lead_id))
    if lead is None:
        raise PaymentBindingError(f"Unknown lead_id={lead_id}")

    expected = _expected_booking_id_for_lead(int(lead_id))
    if booking_id != expected:
        raise PaymentBindingError(f"booking_id must be '{expected}' for lead_id={lead_id}")

    bs = (getattr(lead, "booking_status", None) or "").strip().lower()
    if not bs:
        raise PaymentBindingError("Lead has no booking_status; create/confirm booking before taking payment")
    if bs in ("cancelled", "canceled"):
        raise PaymentBindingError("Cannot create payment for a cancelled booking")

    lead_cur = (getattr(lead, "booking_currency", None) or "").strip()
    if lead_cur and currency != lead_cur:
        raise PaymentBindingError(f"Currency mismatch: lead booking_currency={lead_cur} payment currency={currency}")

    lead_val = getattr(lead, "booking_value", None)
    try:
        lead_val_f = float(lead_val) if lead_val is not None else 0.0
    except Exception:
        lead_val_f = 0.0

    if lead_val_f > 0 and float(amount) > lead_val_f:
        raise PaymentBindingError(f"Amount exceeds booking_value: {amount} > {lead_val_f}")


def create_payment(
    db_path: str,
    *,
    payment_id: str,
    booking_id: str,
    lead_id: int,
    amount: float,
    currency: str = "THB",
    provider: PaymentProvider = PaymentProvider.manual,
    method: PaymentMethod = PaymentMethod.other,
    status: PaymentStatus = PaymentStatus.pending,
    external_ref: Optional[str] = None,
    meta_json: Optional[Dict[str, Any]] = None,
    created_at: Optional[datetime] = None,
) -> Payment:
    """Create a payment record.

    v1: registry-enforced provider/method; external_ref required by some providers.
    """
    init_db(db_path)

    validate_payment_provider_method(provider, method)
    validate_external_ref(provider, external_ref)

    _validate_payment_booking_binding(db_path, booking_id=booking_id, lead_id=lead_id, amount=amount, currency=currency)

    now = datetime.utcnow()
    created = created_at or now
    updated = now

    meta_json = meta_json or {}
    meta_s = json.dumps(meta_json, ensure_ascii=False)

    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO payments (
                payment_id, booking_id, lead_id,
                amount, currency, provider, method, status,
                external_ref, created_at, updated_at, meta_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payment_id, booking_id, int(lead_id),
                float(amount), currency, provider.value, method.value, status.value,
                external_ref, created.isoformat(), updated.isoformat(), meta_s
            ),
        )

    _ensure_reconciliation_default(db_path, payment_id=payment_id, currency=currency, amount=float(amount))

    # OP-PAY-001C: emit payment.created event (state-driving) + correlation link to lead
    EventBus.emit_topic(
        db_path,
        topic="op.payment.created",
        aggregate_type="payment",
        aggregate_id=payment_id,
        correlation_id=f"lead:{int(lead_id)}",
        payload={
            "payment_id": payment_id,
            "booking_id": booking_id,
            "lead_id": int(lead_id),
            "amount": float(amount),
            "currency": currency,
            "status": status.value,
            "provider": provider.value,
            "method": method.value,
            "external_ref": external_ref,
        },
        occurred_at=created,
    )



    return Payment(
        payment_id=payment_id,
        booking_id=booking_id,
        lead_id=int(lead_id),
        amount=float(amount),
        currency=currency,
        provider=provider,
        method=method,
        status=status,
        external_ref=external_ref,
        created_at=created,
        updated_at=updated,
        meta_json=meta_json,
    )


def get_payment(db_path: str, payment_id: str) -> Optional[Payment]:
    init_db(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """SELECT * FROM payments WHERE payment_id = ?""",
            (payment_id,),
        ).fetchone()
    if not row:
        return None

    return Payment(
        payment_id=row["payment_id"],
        booking_id=row["booking_id"],
        lead_id=int(row["lead_id"]),
        amount=float(row["amount"]),
        currency=row["currency"],
        provider=PaymentProvider(row["provider"]),
        method=PaymentMethod(row["method"]),
        status=PaymentStatus(row["status"]),
        external_ref=row["external_ref"],
        created_at=_dt(row["created_at"]),
        updated_at=_dt(row["updated_at"]),
        meta_json=json.loads(row["meta_json"] or "{}"),
    )


def list_payments(
    db_path: str,
    *,
    booking_id: Optional[str] = None,
    lead_id: Optional[int] = None,
    status: Optional[PaymentStatus] = None,
    client_id: Optional[str] = None,
    limit: int = 200,
) -> List[Payment]:
    init_db(db_path)

    if client_id:
        sql = """SELECT p.* FROM payments p
                 INNER JOIN lead_intake l ON p.lead_id = l.lead_id AND l.client_id = ?
                 WHERE 1=1"""
        params: List[Any] = [client_id]
    else:
        sql = "SELECT * FROM payments WHERE 1=1"
        params = []

    tbl = "p." if client_id else ""
    if booking_id is not None:
        sql += f" AND {tbl}booking_id = ?"
        params.append(booking_id)
    if lead_id is not None:
        sql += f" AND {tbl}lead_id = ?"
        params.append(int(lead_id))
    if status is not None:
        sql += f" AND {tbl}status = ?"
        params.append(status.value)

    sql += f" ORDER BY {tbl}created_at ASC LIMIT ?"
    params.append(int(limit))

    with connect(db_path) as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()

    items: List[Payment] = []
    for row in rows:
        items.append(
            Payment(
                payment_id=row["payment_id"],
                booking_id=row["booking_id"],
                lead_id=int(row["lead_id"]),
                amount=float(row["amount"]),
                currency=row["currency"],
                provider=PaymentProvider(row["provider"]),
                method=PaymentMethod(row["method"]),
                status=PaymentStatus(row["status"]),
                external_ref=row["external_ref"],
                created_at=_dt(row["created_at"]),
                updated_at=_dt(row["updated_at"]),
                meta_json=json.loads(row["meta_json"] or "{}"),
            )
        )
    return items


def update_payment_status(
    db_path: str,
    *,
    payment_id: str,
    status: PaymentStatus,
    external_ref: Optional[str] = None,
    meta_patch: Optional[Dict[str, Any]] = None,
) -> Optional[Payment]:
    """Update payment status and optional fields.

    v1 enforces minimal booking binding invariants for sensitive statuses (e.g., captured).
    """
    init_db(db_path)

    existing = get_payment(db_path, payment_id)
    if not existing:
        return None

    # validate external_ref requirement for provider
    validate_external_ref(existing.provider, external_ref or existing.external_ref)

    # Binding invariants against current lead/booking state
    from .repo_leads import get_lead
    lead = get_lead(db_path, int(existing.lead_id))
    if lead is None:
        raise PaymentBindingError(f"Unknown lead_id={existing.lead_id}")
    bs = (getattr(lead, "booking_status", None) or "").strip().lower()
    if bs in ("cancelled", "canceled"):
        raise PaymentBindingError("Cannot update payment for a cancelled booking")

    if status == PaymentStatus.captured and bs not in ("confirmed", "completed"):
        raise PaymentBindingError("Cannot capture payment unless booking is confirmed or completed")

    meta = dict(existing.meta_json or {})
    if meta_patch:
        meta.update(meta_patch)

    now = datetime.utcnow()
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE payments
               SET status = ?,
                   external_ref = ?,
                   updated_at = ?,
                   meta_json = ?
             WHERE payment_id = ?
            """,
            (
                status.value,
                external_ref or existing.external_ref,
                now.isoformat(),
                json.dumps(meta, ensure_ascii=False),
                payment_id,
            ),
        )

    updated = get_payment(db_path, payment_id)
    if updated is None:
        return None

    # OP-PAY-001C: emit payment status events
    # Backfill state if this payment existed before op-events were introduced.
    cur_state = get_state(db_path, aggregate_type="payment", aggregate_id=payment_id)
    if cur_state is None:
        try:
            EventBus.emit_topic(
                db_path,
                topic="op.payment.created",
                aggregate_type="payment",
                aggregate_id=payment_id,
                correlation_id=f"lead:{int(updated.lead_id)}",
                payload={
                    "payment_id": updated.payment_id,
                    "booking_id": updated.booking_id,
                    "lead_id": int(updated.lead_id),
                    "amount": float(updated.amount),
                    "currency": updated.currency,
                    "status": PaymentStatus.pending.value,
                    "provider": updated.provider.value,
                    "method": updated.method.value,
                    "external_ref": updated.external_ref,
                },
                occurred_at=updated.created_at,
            )
        except Exception:
            pass

    prior_status = existing.status.value
    new_status = updated.status.value
    if prior_status != new_status:
        EventBus.emit_topic(
            db_path,
            topic="op.payment.status_changed",
            aggregate_type="payment",
            aggregate_id=payment_id,
            correlation_id=f"lead:{int(updated.lead_id)}",
            payload={
                "payment_id": updated.payment_id,
                "lead_id": int(updated.lead_id),
                "from_status": prior_status,
                "to_status": new_status,
            },
            occurred_at=now,
        )

        # Emit a state-driving topic for key statuses
        topic_map = {
            PaymentStatus.authorized: "op.payment.authorized",
            PaymentStatus.failed: "op.payment.failed",
            PaymentStatus.cancelled: "op.payment.cancelled",
            PaymentStatus.refunded: "op.payment.refunded",
        }

        if updated.status == PaymentStatus.captured:
            # allow capture from pending (direct) or from authorized
            cur = get_state(db_path, aggregate_type="payment", aggregate_id=payment_id) or "__none__"
            capture_topic = "op.payment.captured" if cur == "authorized" else "op.payment.captured_direct"
            EventBus.emit_topic(
                db_path,
                topic=capture_topic,
                aggregate_type="payment",
                aggregate_id=payment_id,
                correlation_id=f"lead:{int(updated.lead_id)}",
                payload={
                    "payment_id": updated.payment_id,
                    "lead_id": int(updated.lead_id),
                    "status": updated.status.value,
                },
                occurred_at=now,
            )
        elif updated.status in (PaymentStatus.failed, PaymentStatus.cancelled):
            cur = get_state(db_path, aggregate_type="payment", aggregate_id=payment_id) or "__none__"
            base = topic_map[updated.status]
            topic = f"{base}_after_authorized" if cur == "authorized" else base
            EventBus.emit_topic(
                db_path,
                topic=topic,
                aggregate_type="payment",
                aggregate_id=payment_id,
                correlation_id=f"lead:{int(updated.lead_id)}",
                payload={
                    "payment_id": updated.payment_id,
                    "lead_id": int(updated.lead_id),
                    "status": updated.status.value,
                },
                occurred_at=now,
            )
        elif updated.status in topic_map:
            EventBus.emit_topic(
                db_path,
                topic=topic_map[updated.status],
                aggregate_type="payment",
                aggregate_id=payment_id,
                correlation_id=f"lead:{int(updated.lead_id)}",
                payload={
                    "payment_id": updated.payment_id,
                    "lead_id": int(updated.lead_id),
                    "status": updated.status.value,
                },
                occurred_at=now,
            )

    return updated



def get_payment_reconciliation(db_path: str, payment_id: str) -> Optional[PaymentReconciliation]:
    init_db(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM payment_reconciliation WHERE payment_id = ?",
            (payment_id,),
        ).fetchone()
    if not row:
        return None
    return PaymentReconciliation(
        payment_id=row["payment_id"],
        status=ReconciliationStatus(row["status"]),
        matched_amount=float(row["matched_amount"]) if row["matched_amount"] is not None else None,
        matched_currency=row["matched_currency"],
        matched_ref=row["matched_ref"],
        note=row["note"],
        updated_by=row["updated_by"],
        created_at=_dt(row["created_at"]),
        updated_at=_dt(row["updated_at"]),
        evidence_json=json.loads(row["evidence_json"] or "{}"),
    )


def upsert_payment_reconciliation(
    db_path: str,
    *,
    payment_id: str,
    status: ReconciliationStatus,
    matched_amount: Optional[float] = None,
    matched_currency: Optional[str] = None,
    matched_ref: Optional[str] = None,
    note: Optional[str] = None,
    updated_by: Optional[str] = None,
    evidence_patch: Optional[Dict[str, Any]] = None,
) -> PaymentReconciliation:
    """Create or update the reconciliation record for a payment."""
    init_db(db_path)
    now = datetime.utcnow()

    existing = get_payment_reconciliation(db_path, payment_id)
    evidence = dict(existing.evidence_json) if existing else {}
    if evidence_patch:
        evidence.update(evidence_patch)

    created_at = existing.created_at if existing else now

    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO payment_reconciliation (
                payment_id, status, matched_amount, matched_currency, matched_ref,
                note, updated_by, created_at, updated_at, evidence_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(payment_id) DO UPDATE SET
                status=excluded.status,
                matched_amount=excluded.matched_amount,
                matched_currency=excluded.matched_currency,
                matched_ref=excluded.matched_ref,
                note=excluded.note,
                updated_by=excluded.updated_by,
                updated_at=excluded.updated_at,
                evidence_json=excluded.evidence_json
            """,
            (
                payment_id,
                status.value,
                float(matched_amount) if matched_amount is not None else None,
                matched_currency,
                matched_ref,
                note,
                updated_by,
                created_at.isoformat(),
                now.isoformat(),
                json.dumps(evidence, ensure_ascii=False),
            ),
        )
    rec = get_payment_reconciliation(db_path, payment_id)
    assert rec is not None
    return rec


def list_payments_reconciliation(
    db_path: str,
    *,
    status: Optional[ReconciliationStatus] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """List payments joined with reconciliation records.

    If status is None, returns all payments with their reconciliation (or default unmatched).
    """
    init_db(db_path)

    sql = """
        SELECT p.*, r.status AS r_status, r.matched_amount AS r_matched_amount,
               r.matched_currency AS r_matched_currency, r.matched_ref AS r_matched_ref,
               r.note AS r_note, r.updated_by AS r_updated_by,
               r.created_at AS r_created_at, r.updated_at AS r_updated_at,
               r.evidence_json AS r_evidence_json
          FROM payments p
          LEFT JOIN payment_reconciliation r ON r.payment_id = p.payment_id
         WHERE 1=1
    """
    params: List[Any] = []

    if status is not None:
        sql += " AND COALESCE(r.status, ?) = ?"
        params.extend([ReconciliationStatus.unmatched.value, status.value])

    sql += " ORDER BY p.created_at ASC LIMIT ?"
    params.append(int(limit))

    with connect(db_path) as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()

    out: List[Dict[str, Any]] = []
    for row in rows:
        pay = Payment(
            payment_id=row["payment_id"],
            booking_id=row["booking_id"],
            lead_id=int(row["lead_id"]),
            amount=float(row["amount"]),
            currency=row["currency"],
            provider=PaymentProvider(row["provider"]),
            method=PaymentMethod(row["method"]),
            status=PaymentStatus(row["status"]),
            external_ref=row["external_ref"],
            created_at=_dt(row["created_at"]),
            updated_at=_dt(row["updated_at"]),
            meta_json=json.loads(row["meta_json"] or "{}"),
        )

        # ensure default reconciliation exists
        if row["r_status"] is None:
            _ensure_reconciliation_default(db_path, payment_id=pay.payment_id, currency=pay.currency, amount=float(pay.amount))
            rec = get_payment_reconciliation(db_path, pay.payment_id)
        else:
            rec = PaymentReconciliation(
                payment_id=pay.payment_id,
                status=ReconciliationStatus(row["r_status"]),
                matched_amount=float(row["r_matched_amount"]) if row["r_matched_amount"] is not None else None,
                matched_currency=row["r_matched_currency"],
                matched_ref=row["r_matched_ref"],
                note=row["r_note"],
                updated_by=row["r_updated_by"],
                created_at=_dt(row["r_created_at"]),
                updated_at=_dt(row["r_updated_at"]),
                evidence_json=json.loads(row["r_evidence_json"] or "{}"),
            )

        out.append({"payment": pay, "reconciliation": rec})
    return out
