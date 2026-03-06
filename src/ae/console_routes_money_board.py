from __future__ import annotations

from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from .console_support import require_role, _resolve_db
from . import repo
from .chat_templates import render_template
from .repo_chat_messages import insert_message as insert_chat_message
from .repo_chat_conversations import get_or_create_conversation as get_or_create_chat_conversation, list_conversations
from .console_routes_chat_public import _find_channel_for_client
from datetime import datetime

admin_router = APIRouter(prefix="/api/money-board", tags=["money-board"])

_admin = require_role("operator")


# Simplified 4-column money board
COLUMN_STATUSES = [
    "pending",     # NEW, PACKAGE_SELECTED, TIME_WINDOW_SET, DEPOSIT_REQUESTED
    "confirmed",   # CONFIRMED
    "complete",    # COMPLETE
    "closed",      # CLOSED, CANCELLED, EXPIRED
]


def _map_status_to_column(status: str) -> str:
    """Map Booking.status to simplified money board column."""
    s = (status or "").strip().upper()
    if s in ("NEW", "PACKAGE_SELECTED", "TIME_WINDOW_SET", "DEPOSIT_REQUESTED"):
        return "pending"
    if s == "CONFIRMED":
        return "confirmed"
    if s == "COMPLETE":
        return "complete"
    if s in ("CLOSED", "CANCELLED", "EXPIRED"):
        return "closed"
    return "pending"


def _get_status_for_lead(lead, booking_request, payment_intent) -> str:
    """Determine which column a lead belongs to based on its state."""
    if not booking_request:
        return "new"
    
    status = booking_request.get("status", "")
    preferred_window = booking_request.get("preferred_window")
    
    if status == "requested":
        # Check if time window is set
        if preferred_window:
            return "time_window_set"
        return "package_selected"
    elif status == "deposit_requested":
        if payment_intent and payment_intent.get("status") == "paid":
            return "confirmed"
        return "deposit_requested"
    elif status == "confirmed":
        return "confirmed"
    elif status == "completed":
        return "complete"
    elif status == "closed":
        return "closed"
    
    return "new"


@admin_router.get("")
def get_money_board(request: Request, _=Depends(_admin)):
    """Get money board data (simplified 4-column layout)."""
    try:
        db_path = _resolve_db(request.query_params.get("db"))
        client_id = request.query_params.get("client_id")
        
        items = repo.get_money_board_bookings(db_path, client_id)
        
        columns: Dict[str, List[Dict[str, Any]]] = {status: [] for status in COLUMN_STATUSES}
        
        for item in items:
            col = _map_status_to_column(item.get("status", ""))
            deposit_req = bool(item.get("deposit_required")) and (
                (item.get("deposit_status") or "").lower() == "requested"
            )
            
            row = {
                "lead_id": item.get("lead_id") or item.get("booking_id"), 
                "booking_id": item["booking_id"],
                "lead_name": item.get("display_name", ""),
                "lead_phone": item.get("phone") or "",
                "lead_email": item.get("email") or "",
                
                "package_id": item.get("package_id", ""),
                "package_name": item.get("package_name_snapshot", ""),
                "package_price": item.get("price_amount", 0),
                
                "preferred_window": item.get("preferred_time_window"),
                "amount": item.get("deposit_amount") if item.get("deposit_required") else item.get("price_amount", 0),
                
                "status": (item.get("status") or "").lower(), 
                "deposit_requested": deposit_req,
                
                "request_id": item["booking_id"], 
            }
            columns[col].append(row)

        return {
            "columns": [
                {"status": status, "count": len(col_items), "items": col_items}
                for status, col_items in columns.items()
            ]
        }
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=str(e))

# ... (Templates/Messaging endpoints can stay similar, just updated to use Customer/Booking if needed)
# For v1 refactor, we focus on the Action buttons.

from .service_booking import BookingService


# Request Models
class SetPackageRequest(BaseModel):
    package_id: str

class SetTimeWindowRequest(BaseModel):
    preferred_window: str
    location: Optional[str] = None

class RequestDepositRequest(BaseModel):
    amount: float
    method: str  # "promptpay" | "stripe" | "bank"
    payment_link: Optional[str] = None

class SendTemplateRequest(BaseModel):
    lead_id: int
    template_key: str
    context: Dict[str, Any] = {}

# ... (Endpoints follow)

@admin_router.post("/{lead_id}/send-package-menu")
def send_package_menu(lead_id: int, request: Request, _=Depends(_admin)):
    """Send package menu template to lead."""
    db_path = _resolve_db(request.query_params.get("db"))
    
    # Get active packages for context
    packages = repo.list_packages(db_path, active=True, limit=20)
    package_list = "\n".join([
        f"{i+1}. {p.name} - ฿{p.price:.0f} ({p.duration_min} min)"
        for i, p in enumerate(packages)
    ])
    
    payload = SendTemplateRequest(
        lead_id=lead_id,
        template_key="money_board.package_menu",
        context={"package_list": package_list},
    )
    return send_template(payload, request, _)

from .service_booking import BookingService

@admin_router.post("/{id}/set-package")
def set_package(id: str, payload: SetPackageRequest, request: Request, _=Depends(_admin)):
    db_path = _resolve_db(request.query_params.get("db"))
    svc = BookingService(db_path)
    
    # Check if ID looks like booking_id (bk_...)
    booking_id = id
    if not id.startswith("bk_"):
         # For v2, we assume leads promoted to bookings have bk_ ids.
         # If raw lead_id passed (e.g. "123"), try to find booking or fail.
         # For simplicity, we assume frontend sends booking_id.
         pass
         
    try:
        svc.set_package(booking_id, payload.package_id, "operator")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@admin_router.post("/{id}/set-time-window")
def set_time_window(id: str, payload: SetTimeWindowRequest, request: Request, _=Depends(_admin)):
    db_path = _resolve_db(request.query_params.get("db"))
    svc = BookingService(db_path)
    try:
        svc.set_time_window(id, payload.preferred_window, "operator")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@admin_router.post("/{id}/request-deposit")
def request_deposit(id: str, payload: RequestDepositRequest, request: Request, _=Depends(_admin)):
    db_path = _resolve_db(request.query_params.get("db"))
    svc = BookingService(db_path)
    try:
        svc.request_deposit(id, payload.amount, payload.payment_link, "operator")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@admin_router.post("/{id}/mark-paid")
def mark_paid(id: str, request: Request, _=Depends(_admin)):
    db_path = _resolve_db(request.query_params.get("db"))
    svc = BookingService(db_path)
    try:
        svc.mark_deposit_paid(id, "manual-mark", "operator")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@admin_router.post("/{id}/confirm")
def confirm_booking(id: str, request: Request, _=Depends(_admin)):
    """Confirm a booking (TIME_WINDOW_SET or DEPOSIT_REQUESTED -> CONFIRMED)."""
    db_path = _resolve_db(request.query_params.get("db"))
    svc = BookingService(db_path)
    try:
        svc.confirm_booking(id, actor_id="operator", override_reason="money_board_confirm")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@admin_router.post("/{id}/mark-completed")
def mark_completed(id: str, request: Request, _=Depends(_admin)):
    db_path = _resolve_db(request.query_params.get("db"))
    svc = BookingService(db_path)
    try:
        svc.mark_complete(id, "operator")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@admin_router.post("/{id}/close")
def close_booking(id: str, request: Request, _=Depends(_admin)):
    db_path = _resolve_db(request.query_params.get("db"))
    svc = BookingService(db_path)
    try:
        svc.close_booking(id, "operator")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@admin_router.post("/clear-legacy-data")
def clear_legacy_data(request: Request, _=Depends(_admin)):
    """Dev tool: Wipe all bookings and customers to start fresh."""
    db_path = _resolve_db(request.query_params.get("db"))
    import sqlite3
    con = sqlite3.connect(db_path)
    con.execute("DELETE FROM booking_events")
    con.execute("DELETE FROM bookings")
    con.execute("DELETE FROM customers")
    con.execute("DELETE FROM lead_intake") # Also clear raw leads to prevent resync
    con.commit()
    con.close()
    return {"status": "cleared"}


def _sync_new_leads_to_bookings(db_path: str, client_id: str = None):
    # Find leads that don't have a booking
    svc = BookingService(db_path)
    
    # 1. Get raw leads
    leads = repo.list_leads(db_path, limit=50, client_id=client_id)
    # 2. Get existing booking lead_ids
    import sqlite3
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    try:
        # Check if table has lead_id column first (migration added it)
        existing = set(r[0] for r in cursor.execute("SELECT lead_id FROM bookings WHERE lead_id IS NOT NULL").fetchall())
    except Exception:
        existing = set()
    con.close()
    
    for lead in leads:
        if lead.lead_id not in existing:
            # Promote to Booking
            if lead.status == "new": # Only new leads
                lead_data = {
                    "lead_id": lead.lead_id,
                    "name": lead.name,
                    "phone": lead.phone,
                    "email": lead.email,
                    "telegram_username": lead.meta_json.get("telegram_username"),
                    "telegram_id": lead.meta_json.get("telegram_chat_id"),
                    "source": lead.source
                }
                client = lead.client_id or client_id or "default"
                svc.create_lead_booking(client, lead_data)


# Update GET to sync first
@admin_router.get("/sync-and-get")
def sync_and_get_money_board(request: Request, _=Depends(_admin)):
    db_path = _resolve_db(request.query_params.get("db"))
    client_id = request.query_params.get("client_id")
    
    _sync_new_leads_to_bookings(db_path, client_id)
    
    return get_money_board(request, _)


@admin_router.post("/send-template")
def send_template(payload: SendTemplateRequest, request: Request, _=Depends(_admin)):
    """Send a template message to a lead's chat channel."""
    db_path = _resolve_db(request.query_params.get("db"))
    
    # Get lead
    lead = repo.get_lead(db_path, payload.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    
    # Get client_id from lead
    if not lead.client_id:
        raise HTTPException(status_code=400, detail="lead_missing_client_id")
    
    # Find channel for this client
    channel = _find_channel_for_client(db_path, lead.client_id)
    if not channel:
        raise HTTPException(
            status_code=400, 
            detail=f"no_chat_channel_configured_for_client_{lead.client_id}"
        )
    
    # Check for existing conversation for this lead
    existing_conversations = list_conversations(
        db_path,
        lead_id=str(payload.lead_id),
        limit=1
    )
    
    if existing_conversations:
        # Reuse existing conversation
        conversation = existing_conversations[0]
        # Update conversation if channel changed (shouldn't happen, but be safe)
        if conversation.channel_id != channel.channel_id:
            conversation = get_or_create_chat_conversation(
                db_path,
                conversation_id=conversation.conversation_id,
                channel_id=channel.channel_id,
                external_thread_id=conversation.external_thread_id or f"lead-{payload.lead_id}",
                lead_id=str(payload.lead_id),
            )
    else:
        # Create new conversation
        conversation = get_or_create_chat_conversation(
            db_path,
            conversation_id=f"conv_lead_{payload.lead_id}_{int(datetime.utcnow().timestamp())}",
            channel_id=channel.channel_id,
            external_thread_id=f"lead-{payload.lead_id}",
            lead_id=str(payload.lead_id),
        )
    
    # Build context with lead/booking/package data
    context = payload.context.copy()
    
    # Add lead info
    context.setdefault("lead_name", lead.name or "Customer")
    context.setdefault("lead_phone", lead.phone or "")
    
    # Add booking/package info if available
    booking_requests = repo.list_booking_requests(db_path, lead_id=payload.lead_id, limit=1)
    if booking_requests:
        br = booking_requests[0]
        context.setdefault("preferred_window", br.preferred_window or "")
        context.setdefault("location", br.location or "")
        
        # Get package info
        if br.package_id:
            pkg = repo.get_package(db_path, br.package_id)
            if pkg:
                context.setdefault("package_name", pkg.name)
                context.setdefault("package_price", pkg.price)
                
                # Build package list for package_menu template
                if payload.template_key == "money_board.package_menu":
                    all_packages = repo.list_packages(db_path, active=True, limit=20)
                    package_list = "\n".join([
                        f"{i+1}. {p.name} - ฿{p.price:.0f} ({p.duration_min} min)"
                        for i, p in enumerate(all_packages)
                    ])
                    context.setdefault("package_list", package_list)
        
        # Get payment intent info
        payment_intents = repo.list_payment_intents(db_path, booking_request_id=br.request_id, limit=1)
        if payment_intents:
            pi = payment_intents[0]
            context.setdefault("amount", pi.amount)
            context.setdefault("payment_link", pi.payment_link or "")
    
    # Render template
    try:
        message_text = render_template(db_path, payload.template_key, context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Deliver via Telegram if channel is Telegram
    try:
        from .telegram_delivery import send_message
        send_message(db_path, conversation.conversation_id, message_text)
    except Exception:
        # Best-effort: don't fail if Telegram delivery fails
        pass
    
    # Create message record
    message_id = f"msg_{datetime.utcnow().isoformat().replace(':', '-').replace('.', '-')}_{payload.lead_id}"
    insert_chat_message(
        db_path,
        message_id=message_id,
        conversation_id=conversation.conversation_id,
        direction="outbound",
        text=message_text,
        ts=datetime.utcnow().isoformat() + "Z",
    )
    
    return {
        "message_id": message_id,
        "conversation_id": conversation.conversation_id,
        "text": message_text,
        "template_key": payload.template_key,
    }
