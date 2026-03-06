"""Telegram webhook handler.

Receives updates from Telegram and integrates with existing chat system.
Reuses existing functions: get_or_create_conversation, insert_message, EventBus.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request, HTTPException

from .console_support import _resolve_db_path
from .public_guard import rate_limit_or_429
from .repo_chat_conversations import get_or_create_conversation, get_conversation
from .repo_chat_messages import insert_message
from .repo_chat_channels import list_chat_channels
from .event_bus import EventBus
from .enums import ChatProvider
from . import repo

public_router = APIRouter()


def _find_telegram_channel(db_path: str, client_id: Optional[str] = None) -> Optional[Any]:
    """Find Telegram channel, optionally filtered by client_id."""
    channels = list_chat_channels(db_path, provider=ChatProvider.telegram, limit=50)
    
    if not channels:
        return None
    
    # If client_id specified, filter by it
    if client_id:
        client_channels = [
            ch for ch in channels
            if ch.meta_json.get("client_id") == client_id
        ]
        if client_channels:
            return client_channels[0]
        return None
    
    # Return first Telegram channel
    return channels[0]


async def _handle_message(db_path: str, channel: Any, message: Dict[str, Any]) -> None:
    """Handle incoming Telegram message."""
    chat_id = str(message["chat"]["id"])
    text = message.get("text", "")
    message_id = str(message["message_id"])
    from_user = message.get("from", {})
    username = from_user.get("username")
    
    # Get or create conversation (reuse existing function)
    conversation_id = f"conv_telegram_{chat_id}"
    conversation = get_or_create_conversation(
        db_path,
        conversation_id=conversation_id,
        channel_id=channel.channel_id,
        external_thread_id=str(chat_id),  # Store Telegram chat_id here
        meta_json={
            "telegram_chat_id": chat_id,
            "telegram_username": username,
        }
    )
    
    # Store message (reuse existing function)
    insert_message(
        db_path,
        conversation_id=conversation.conversation_id,
        direction="inbound",
        text=text,
        external_msg_id=message_id,
        payload_json={"telegram_message": message},
        ts=datetime.utcnow()
    )
    
    # Emit event (reuse existing function)
    EventBus.emit_topic(
        db_path,
        topic="op.chat.message_received",
        aggregate_type="chat",
        aggregate_id=conversation.conversation_id,
        payload={
            "conversation_id": conversation.conversation_id,
            "text": text,
            "channel": "telegram",
            "chat_id": chat_id
        },
        correlation_id=None,
    )
    
    # Handle /start command with deep link
    if text.startswith("/start"):
        args = text.split()[1:] if len(text.split()) > 1 else []
        if args and args[0].startswith("package_"):
            package_id = args[0].replace("package_", "")
            await _handle_package_deep_link(db_path, conversation, channel, package_id)


async def _handle_callback_query(db_path: str, channel: Any, callback: Dict[str, Any]) -> None:
    """Handle Telegram callback query (button clicks)."""
    # TODO: Implement callback query handling for inline keyboards
    # For now, just acknowledge the callback
    pass


async def _handle_package_deep_link(
    db_path: str,
    conversation: Any,
    channel: Any,
    package_id: str
) -> None:
    """Handle package deep link from landing page.
    
    When user clicks package on landing page, they're redirected to:
    t.me/bot?start=package_pkg123
    
    This function confirms the package selection and guides user through booking.
    """
    # Get package info
    package = repo.get_package(db_path, package_id)
    if not package:
        # Package not found - send error message
        from .telegram_delivery import send_message
        send_message(
            db_path,
            conversation.conversation_id,
            "Sorry, the selected package is no longer available. Please visit our website to see current packages."
        )
        return
    
    # Store package_id in conversation meta for later use
    conversation_meta = conversation.meta_json.copy()
    conversation_meta["pending_package_id"] = package_id
    
    # Update conversation with package info
    get_or_create_conversation(
        db_path,
        conversation_id=conversation.conversation_id,
        channel_id=conversation.channel_id,
        external_thread_id=conversation.external_thread_id,
        meta_json=conversation_meta
    )
    
    # Send package confirmation message
    from .telegram_delivery import send_message
    message = f"""✅ Package Selected!

📦 {package.name}
💰 ฿{package.price:.0f}
⏱️ {package.duration_min} minutes

Confirm this package?
Reply with "yes" to continue or "no" to choose a different package."""
    
    send_message(db_path, conversation.conversation_id, message)


@public_router.post("/v1/telegram/webhook")
async def telegram_webhook(request: Request):
    """Handle Telegram webhook updates.
    
    This endpoint receives POST requests from Telegram when users interact with the bot.
    Reuses existing chat infrastructure for message storage and event handling.
    """
    rate_limit_or_429(request)
    db_path = _resolve_db_path(request.query_params.get("db"))
    
    if not db_path:
        raise HTTPException(status_code=400, detail="db parameter required")
    
    try:
        update = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    
    # Find Telegram channel
    # Try to get client_id from update if available (future enhancement)
    channel = _find_telegram_channel(db_path)
    if not channel:
        # No Telegram channel configured - silently ignore
        return {"ok": True}
    
    # Handle message or callback_query
    if "message" in update:
        await _handle_message(db_path, channel, update["message"])
    elif "callback_query" in update:
        await _handle_callback_query(db_path, channel, update["callback_query"])
    
    return {"ok": True}
