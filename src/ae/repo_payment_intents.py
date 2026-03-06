from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from . import db
from .models import PaymentIntent
from .event_bus import EventBus
from .enums import PaymentProvider, PaymentMethod, PaymentStatus


def _now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def create_payment_intent(db_path: str, intent: PaymentIntent) -> PaymentIntent:
    """Create a new payment intent and emit event."""
    db.init_db(db_path)
    if isinstance(intent.created_at, datetime):
        created_at = intent.created_at.replace(microsecond=0).isoformat() + "Z"
    else:
        created_at = intent.created_at or _now()
    updated_at = _now()
    meta_json = json.dumps(intent.meta_json or {}, ensure_ascii=False, separators=(",", ":"))
    
    con = db.connect(db_path)
    try:
        con.execute(
            """INSERT INTO payment_intents(
                intent_id, lead_id, booking_request_id, amount, method, status, payment_link, meta_json, created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                intent.intent_id,
                intent.lead_id,
                intent.booking_request_id,
                intent.amount,
                intent.method,
                intent.status,
                intent.payment_link,
                meta_json,
                created_at,
                updated_at,
            ),
        )
        con.commit()
    finally:
        con.close()
    
    # Emit event for state machine
    if intent.status == "requested":
        try:
            EventBus.emit_topic(
                db_path,
                topic="op.payment_intent.requested",
                aggregate_type="payment_intent",
                aggregate_id=intent.intent_id,
                payload={
                    "intent_id": intent.intent_id,
                    "lead_id": intent.lead_id,
                    "booking_request_id": intent.booking_request_id,
                    "amount": intent.amount,
                    "method": intent.method,
                },
                actor="operator",
                correlation_id=f"lead:{intent.lead_id}",
                causation_id=None,
            )
        except Exception:
            # Best-effort: don't fail if event emission fails
            pass
    
    return PaymentIntent(
        intent_id=intent.intent_id,
        lead_id=intent.lead_id,
        booking_request_id=intent.booking_request_id,
        amount=intent.amount,
        method=intent.method,
        status=intent.status,
        payment_link=intent.payment_link,
        meta_json=intent.meta_json or {},
        created_at=datetime.fromisoformat(created_at),
        updated_at=datetime.fromisoformat(updated_at),
    )


def get_payment_intent_client_id(db_path: str, intent_id: str) -> Optional[str]:
    """Return client_id for a payment intent (via lead→lead_intake)."""
    db.init_db(db_path)
    con = db.connect(db_path)
    try:
        row = db.fetchone(
            con,
            """SELECT li.client_id FROM payment_intents pi
               JOIN lead_intake li ON pi.lead_id = li.lead_id
               WHERE pi.intent_id = ?""",
            (intent_id,),
        )
        return row["client_id"] if row and row.get("client_id") else None
    finally:
        con.close()


def get_payment_intent(db_path: str, intent_id: str) -> Optional[PaymentIntent]:
    """Get a payment intent by ID."""
    db.init_db(db_path)
    con = db.connect(db_path)
    try:
        row = db.fetchone(con, "SELECT * FROM payment_intents WHERE intent_id=?", (intent_id,))
        if not row:
            return None
        return PaymentIntent(
            intent_id=row["intent_id"],
            lead_id=row["lead_id"],
            booking_request_id=row["booking_request_id"],
            amount=row["amount"],
            method=row["method"],
            status=row["status"],
            payment_link=row["payment_link"],
            meta_json=json.loads(row["meta_json"] or "{}"),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
    finally:
        con.close()


def list_payment_intents(
    db_path: str,
    *,
    booking_request_id: Optional[str] = None,
    status: Optional[str] = None,
    client_id: Optional[str] = None,
    limit: int = 50,
) -> List[PaymentIntent]:
    """List payment intents with optional filters.
    When client_id is set, filters via lead→lead_intake.client_id."""
    db.init_db(db_path)
    sql = "SELECT pi.* FROM payment_intents pi"
    params: List[Any] = []
    where: List[str] = []
    if client_id:
        sql += " JOIN lead_intake li ON pi.lead_id = li.lead_id"
        where.append("li.client_id=?")
        params.append(client_id)
    if booking_request_id:
        where.append("pi.booking_request_id=?")
        params.append(booking_request_id)
    if status:
        where.append("pi.status=?")
        params.append(status)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY pi.created_at DESC LIMIT ?"
    params.append(limit)
    
    con = db.connect(db_path)
    try:
        rows = db.fetchall(con, sql, tuple(params))
        out: List[PaymentIntent] = []
        for r in rows:
            out.append(PaymentIntent(
                intent_id=r["intent_id"],
                lead_id=r["lead_id"],
                booking_request_id=r["booking_request_id"],
                amount=r["amount"],
                method=r["method"],
                status=r["status"],
                payment_link=r["payment_link"],
                meta_json=json.loads(r["meta_json"] or "{}"),
                created_at=datetime.fromisoformat(r["created_at"]),
                updated_at=datetime.fromisoformat(r["updated_at"]),
            ))
        return out
    finally:
        con.close()


def mark_payment_intent_paid(db_path: str, intent_id: str) -> Optional[PaymentIntent]:
    """Mark payment intent as paid, create Payment record, and update BookingRequest."""
    db.init_db(db_path)
    updated_at = _now()
    
    con = db.connect(db_path)
    try:
        # Get existing intent
        existing = db.fetchone(con, "SELECT * FROM payment_intents WHERE intent_id=?", (intent_id,))
        if not existing:
            return None
        
        if existing["status"] == "paid":
            # Already paid, return existing
            return get_payment_intent(db_path, intent_id)
        
        # Update intent status
        con.execute(
            "UPDATE payment_intents SET status=?, updated_at=? WHERE intent_id=?",
            ("paid", updated_at, intent_id),
        )
        con.commit()
        
        # Emit event
        try:
            EventBus.emit_topic(
                db_path,
                topic="op.payment_intent.paid",
                aggregate_type="payment_intent",
                aggregate_id=intent_id,
                payload={
                    "intent_id": intent_id,
                    "lead_id": existing["lead_id"],
                    "booking_request_id": existing["booking_request_id"],
                    "amount": existing["amount"],
                },
                actor="operator",
                correlation_id=f"lead:{existing['lead_id']}",
                causation_id=None,
            )
        except Exception:
            # Best-effort: don't fail if event emission fails
            pass
        
        # Create Payment record
        try:
            from . import repo
            payment_id = f"pay_{intent_id}"
            # Use lead-based booking_id format for compatibility with existing validation
            booking_id = f"lead-{existing['lead_id']}"
            
            # Determine provider and method from intent method
            provider_map = {
                "promptpay": PaymentProvider.manual,
                "stripe": PaymentProvider.stripe,
                "bank": PaymentProvider.manual,
            }
            method_map = {
                "promptpay": PaymentMethod.qr,
                "stripe": PaymentMethod.card,
                "bank": PaymentMethod.bank_transfer,
            }
            
            provider = provider_map.get(existing["method"], PaymentProvider.manual)
            method = method_map.get(existing["method"], PaymentMethod.other)
            
            repo.create_payment(
                db_path,
                payment_id=payment_id,
                booking_id=booking_id,
                lead_id=existing["lead_id"],
                amount=existing["amount"],
                currency="THB",  # Default, could be stored in intent
                provider=provider,
                method=method,
                status=PaymentStatus.captured,
                external_ref=None,
                meta_json={"intent_id": intent_id, "booking_request_id": existing["booking_request_id"]},
            )
            
            # Emit payment captured event
            EventBus.emit_topic(
                db_path,
                topic="op.payment.captured_direct",
                aggregate_type="payment",
                aggregate_id=payment_id,
                payload={
                    "payment_id": payment_id,
                    "lead_id": existing["lead_id"],
                    "status": "captured",
                },
                actor="operator",
                correlation_id=f"lead:{existing['lead_id']}",
                causation_id=None,
            )
        except Exception:
            # Best-effort: don't fail if payment creation fails
            pass
        
        # Update BookingRequest status to confirmed
        try:
            from . import repo
            repo.update_booking_status(db_path, existing["booking_request_id"], "confirmed")
        except Exception:
            # Best-effort: don't fail if booking update fails
            pass
        
    finally:
        con.close()
    
    # Return updated intent
    return get_payment_intent(db_path, intent_id)
