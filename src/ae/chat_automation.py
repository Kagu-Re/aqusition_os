
from __future__ import annotations

"""Chat automation hooks and runner (v1).

- Schedules outbound messages as durable tasks (chat_automations)
- A runner executes due tasks, renders templates, inserts outbound messages, emits op events.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from .models import OpEvent
from .repo_chat_conversations import list_conversations, get_conversation
from .repo_chat_messages import insert_message
from .repo_chat_automations import create_automation, list_due_automations, mark_sent
from .chat_templates import render_template
from .event_bus import EventBus
from .repo_activity import append_activity

_CHAT_AUTOMATION_HOOKS_INSTALLED = False


def install_chat_automation_hooks() -> None:
    """Register default automation hooks into GLOBAL_HOOKS.

    Imported lazily to avoid import cycles.
    """
    global _CHAT_AUTOMATION_HOOKS_INSTALLED
    if _CHAT_AUTOMATION_HOOKS_INSTALLED:
        return
    from .hooks import GLOBAL_HOOKS

    GLOBAL_HOOKS.subscribe(name="chat_auto_on_booking_confirmed", pattern="op.booking.confirmed", fn=_on_booking_confirmed)
    GLOBAL_HOOKS.subscribe(name="chat_auto_on_payment_captured", pattern="op.payment.captured", fn=_on_payment_captured)
    GLOBAL_HOOKS.subscribe(name="chat_auto_on_chat_message_received", pattern="op.chat.message_received", fn=_on_message_received)
    # Money board automation hooks
    GLOBAL_HOOKS.subscribe(name="chat_auto_on_booking_request_confirmed", pattern="op.booking.confirmed", fn=_on_booking_request_confirmed)
    GLOBAL_HOOKS.subscribe(name="chat_auto_on_booking_request_completed", pattern="op.booking.completed", fn=_on_booking_request_completed)
    _CHAT_AUTOMATION_HOOKS_INSTALLED = True


def _find_conversation_for_lead(db_path: str, lead_id: str) -> Optional[str]:
    convs = list_conversations(db_path, lead_id=lead_id, limit=5)
    if not convs:
        return None
    return convs[0].conversation_id


def _on_booking_confirmed(db_path: str, ev: OpEvent) -> None:
    lead_id = str(ev.payload.get("lead_id") or ev.payload.get("lead") or "")
    if not lead_id:
        return
    conv_id = _find_conversation_for_lead(db_path, lead_id)
    if not conv_id:
        return
    # immediate confirmation message
    ctx: Dict[str, Any] = {
        "service_date": ev.payload.get("service_date", "?"),
        "lead_id": lead_id,
    }
    create_automation(db_path, conversation_id=conv_id, template_key="booking_confirm", due_at=datetime.utcnow(), context_json=ctx)


def _on_payment_captured(db_path: str, ev: OpEvent) -> None:
    lead_id = str(ev.payload.get("lead_id") or "")
    if not lead_id:
        return
    conv_id = _find_conversation_for_lead(db_path, lead_id)
    if not conv_id:
        return
    ctx: Dict[str, Any] = {
        "amount": ev.payload.get("amount", "?"),
        "currency": ev.payload.get("currency", "?"),
        "lead_id": lead_id,
    }
    # no link in v1
    ctx["payment_link"] = ev.payload.get("payment_link", "received")
    create_automation(db_path, conversation_id=conv_id, template_key="followup_24h", due_at=datetime.utcnow() + timedelta(hours=24), context_json=ctx)


def _on_message_received(db_path: str, ev: OpEvent) -> None:
    conv_id = str(ev.payload.get("conversation_id") or "")
    text = str(ev.payload.get("text") or "").lower()
    if not conv_id or not text:
        return
    if "price" in text or "pay" in text:
        ctx: Dict[str, Any] = {
            "payment_link": ev.payload.get("payment_link", "TBD"),
            "amount": ev.payload.get("amount", "?"),
            "currency": ev.payload.get("currency", "?"),
        }
        create_automation(db_path, conversation_id=conv_id, template_key="payment_request", due_at=datetime.utcnow(), context_json=ctx)


def _on_booking_request_confirmed(db_path: str, ev: OpEvent) -> None:
    """Schedule service reminders when booking_request is confirmed."""
    lead_id = str(ev.payload.get("lead_id") or "")
    request_id = ev.payload.get("request_id") or ""
    if not lead_id:
        return
    
    conv_id = _find_conversation_for_lead(db_path, lead_id)
    if not conv_id:
        return
    
    # Get booking request to find service date
    from .repo_booking_requests import get_booking_request
    booking = get_booking_request(db_path, request_id) if request_id else None
    
    # Calculate service date (for now, use created_at + 1 day as placeholder)
    # In production, this should come from preferred_window + actual scheduling
    if booking:
        service_date = datetime.fromisoformat(booking.created_at.replace("Z", "+00:00")) if isinstance(booking.created_at, str) else booking.created_at
        service_date = service_date.replace(tzinfo=None) if service_date.tzinfo else service_date
    else:
        service_date = datetime.utcnow() + timedelta(days=1)
    
    # Get package info for context
    package_name = "Service"
    time_window = ""
    location = ""
    if booking:
        from .repo_service_packages import get_package
        if booking.package_id:
            pkg = get_package(db_path, booking.package_id)
            if pkg:
                package_name = pkg.name
        time_window = booking.preferred_window or ""
        location = booking.location or ""
    
    # Schedule 24h reminder
    reminder_24h_at = service_date - timedelta(hours=24)
    if reminder_24h_at > datetime.utcnow():
        ctx_24h: Dict[str, Any] = {
            "package_name": package_name,
            "time_window": time_window,
            "lead_id": lead_id,
        }
        create_automation(db_path, conversation_id=conv_id, template_key="money_board.service_reminder_24h", due_at=reminder_24h_at, context_json=ctx_24h)
    
    # Schedule 2h reminder
    reminder_2h_at = service_date - timedelta(hours=2)
    if reminder_2h_at > datetime.utcnow():
        ctx_2h: Dict[str, Any] = {
            "package_name": package_name,
            "time_window": time_window,
            "location": location,
            "lead_id": lead_id,
        }
        create_automation(db_path, conversation_id=conv_id, template_key="money_board.service_reminder_2h", due_at=reminder_2h_at, context_json=ctx_2h)


def _on_booking_request_completed(db_path: str, ev: OpEvent) -> None:
    """Send review request when booking_request is completed."""
    lead_id = str(ev.payload.get("lead_id") or "")
    request_id = ev.payload.get("request_id") or ""
    if not lead_id:
        return
    
    conv_id = _find_conversation_for_lead(db_path, lead_id)
    if not conv_id:
        return
    
    # Get booking request to find package info
    from .repo_booking_requests import get_booking_request
    booking = get_booking_request(db_path, request_id) if request_id else None
    
    package_name = "Service"
    if booking:
        from .repo_service_packages import get_package
        if booking.package_id:
            pkg = get_package(db_path, booking.package_id)
            if pkg:
                package_name = pkg.name
    
    # Schedule review request 1 hour after completion
    ctx: Dict[str, Any] = {
        "package_name": package_name,
        "lead_id": lead_id,
    }
    create_automation(db_path, conversation_id=conv_id, template_key="money_board.review_request", due_at=datetime.utcnow() + timedelta(hours=1), context_json=ctx)


def run_due_chat_automations(db_path: str, *, now: Optional[datetime] = None, limit: int = 50) -> int:
    now = now or datetime.utcnow()
    due = list_due_automations(db_path, now=now, limit=limit)
    sent = 0
    for a in due:
        try:
            body = render_template(db_path, a.template_key, a.context_json)
            
            # Deliver via Telegram if channel is Telegram
            try:
                from .telegram_delivery import send_message
                send_message(db_path, a.conversation_id, body)
            except Exception:
                # Best-effort: don't fail if Telegram delivery fails
                pass
            
            insert_message(db_path, conversation_id=a.conversation_id, direction="outbound", text=body, payload_json={"template_key": a.template_key})
            # Emit op event
            EventBus.emit_topic(
                db_path,
                topic="op.chat.message_sent",
                aggregate_type="chat",
                aggregate_id=a.conversation_id,
                payload={
                    "conversation_id": a.conversation_id,
                    "text": body,
                    "template_key": a.template_key,
                },
                correlation_id=None,
            )
            mark_sent(db_path, a.automation_id, now)
            append_activity(db_path, action="chat_automation_sent", entity_type="chat", entity_id=a.conversation_id, details={"template_key": a.template_key})
            sent += 1
        except Exception as e:
            append_activity(db_path, action="chat_automation_error", entity_type="chat", entity_id=a.conversation_id, details={"error": str(e), "template_key": a.template_key})
    return sent
