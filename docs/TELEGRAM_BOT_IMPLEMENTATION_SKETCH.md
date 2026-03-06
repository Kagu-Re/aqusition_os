# Telegram Bot Implementation Sketch

This document provides code sketches for implementing Telegram bot integration with Moneyboard.

## 1. Telegram Webhook Handler

```python
# src/ae/console_routes_telegram_webhook.py

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
from datetime import datetime

from .console_support import _resolve_db_path
from .public_guard import rate_limit_or_429
from .repo_chat_conversations import get_or_create_conversation
from .repo_chat_messages import insert_message
from .repo_chat_channels import list_chat_channels
from .event_bus import EventBus
from .enums import ChatProvider

public_router = APIRouter()


class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[Dict[str, Any]] = None
    callback_query: Optional[Dict[str, Any]] = None


@public_router.post("/v1/telegram/webhook")
async def telegram_webhook(request: Request):
    """Handle Telegram webhook updates."""
    rate_limit_or_429(request)
    
    # Get bot token from request or config
    db_path = _resolve_db_path(request.query_params.get("db"))
    webhook_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    
    # Verify webhook secret if configured
    # (Telegram supports secret token for webhook validation)
    
    try:
        body = await request.json()
        update = TelegramUpdate(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid update: {e}")
    
    # Handle message
    if update.message:
        await _handle_message(db_path, update.message)
    
    # Handle callback query (button clicks)
    elif update.callback_query:
        await _handle_callback_query(db_path, update.callback_query)
    
    return {"ok": True}


async def _handle_message(db_path: str, message: Dict[str, Any]):
    """Process incoming Telegram message."""
    chat_id = str(message["chat"]["id"])
    text = message.get("text", "")
    message_id = str(message["message_id"])
    from_user = message.get("from", {})
    username = from_user.get("username")
    
    # Find or create conversation
    # Strategy: Look for Telegram channel, then find conversation by chat_id
    channels = list_chat_channels(db_path, provider=ChatProvider.telegram, limit=10)
    if not channels:
        # No Telegram channel configured
        return
    
    channel = channels[0]  # Use first Telegram channel (could be improved)
    
    # Try to find existing conversation by chat_id
    conversation_id = f"conv_telegram_{chat_id}"
    conversation = get_or_create_conversation(
        db_path,
        conversation_id=conversation_id,
        channel_id=channel.channel_id,
        external_thread_id=chat_id,  # Store Telegram chat_id here
        meta_json={"telegram_chat_id": chat_id, "telegram_username": username}
    )
    
    # Insert inbound message
    insert_message(
        db_path,
        conversation_id=conversation.conversation_id,
        direction="inbound",
        text=text,
        external_msg_id=message_id,
        payload_json={"telegram_message": message},
        ts=datetime.utcnow()
    )
    
    # Emit event to trigger automation
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
        }
    )
    
    # Handle commands
    if text.startswith("/"):
        await _handle_command(db_path, conversation, text)


async def _handle_callback_query(db_path: str, callback: Dict[str, Any]):
    """Handle inline keyboard button clicks."""
    chat_id = str(callback["message"]["chat"]["id"])
    data = callback.get("data", "")  # Custom data from button
    query_id = callback["id"]
    
    # Parse callback data (e.g., "package:123" or "time_window:2026-02-08:10:00")
    # Update booking request accordingly
    # Send confirmation message
    
    # Example: Handle package selection
    if data.startswith("package:"):
        package_id = data.split(":")[1]
        # Update booking request with package_id
        # Send confirmation via Telegram Bot API
        pass


async def _handle_command(db_path: str, conversation, text: str):
    """Handle Telegram commands like /start, /help, /status."""
    if text == "/start":
        # Send welcome message
        # If deep link: t.me/bot?start=lead_123, extract lead_id
        pass
    elif text == "/help":
        # Send help message
        pass
    elif text == "/status":
        # Get booking status for this conversation
        pass
```

## 2. Telegram Bot API Client

```python
# src/ae/telegram_bot_client.py

import httpx
from typing import Optional, List, Dict, Any
import os


class TelegramBotClient:
    """Client for Telegram Bot API."""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def send_message(
        self,
        chat_id: str,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None,
        parse_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a text message."""
        payload = {
            "chat_id": chat_id,
            "text": text,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        if parse_mode:
            payload["parse_mode"] = parse_mode
        
        response = await self.client.post(
            f"{self.api_url}/sendMessage",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False
    ) -> Dict[str, Any]:
        """Answer a callback query (button click)."""
        payload = {
            "callback_query_id": callback_query_id,
        }
        if text:
            payload["text"] = text
        if show_alert:
            payload["show_alert"] = True
        
        response = await self.client.post(
            f"{self.api_url}/answerCallbackQuery",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def create_inline_keyboard(self, buttons: List[List[Dict[str, str]]]) -> Dict[str, Any]:
        """Create inline keyboard markup."""
        return {
            "inline_keyboard": buttons
        }
    
    def create_package_menu_keyboard(self, packages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create inline keyboard for package selection."""
        buttons = []
        for pkg in packages:
            buttons.append([{
                "text": f"{pkg['name']} - ฿{pkg['price']:.0f}",
                "callback_data": f"package:{pkg['package_id']}"
            }])
        return self.create_inline_keyboard(buttons)
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


def get_telegram_bot_client(db_path: str, channel_id: Optional[str] = None) -> Optional[TelegramBotClient]:
    """Get Telegram bot client for a channel."""
    from .repo_chat_channels import get_chat_channel
    
    # Get bot token from channel config or environment
    if channel_id:
        channel = get_chat_channel(db_path, channel_id)
        if channel and channel.provider == ChatProvider.telegram:
            token = channel.meta_json.get("telegram_bot_token")
            if token:
                return TelegramBotClient(token)
    
    # Fallback to environment variable
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if token:
        return TelegramBotClient(token)
    
    return None
```

## 3. Message Delivery Integration

```python
# src/ae/chat_message_delivery.py

from typing import Optional
from .telegram_bot_client import get_telegram_bot_client
from .repo_chat_channels import get_chat_channel
from .repo_chat_conversations import get_conversation
from .enums import ChatProvider


async def deliver_message(
    db_path: str,
    conversation_id: str,
    text: str,
    reply_markup: Optional[Dict[str, Any]] = None
) -> bool:
    """Deliver a message via the appropriate channel."""
    # Get conversation
    conversation = get_conversation(db_path, conversation_id)
    if not conversation:
        return False
    
    # Get channel
    channel = get_chat_channel(db_path, conversation.channel_id)
    if not channel:
        return False
    
    # Deliver via Telegram if Telegram channel
    if channel.provider == ChatProvider.telegram:
        bot_client = get_telegram_bot_client(db_path, channel.channel_id)
        if not bot_client:
            return False
        
        # Get Telegram chat_id from conversation
        chat_id = conversation.external_thread_id or conversation.meta_json.get("telegram_chat_id")
        if not chat_id:
            return False
        
        try:
            await bot_client.send_message(
                chat_id=str(chat_id),
                text=text,
                reply_markup=reply_markup
            )
            return True
        except Exception as e:
            # Log error
            print(f"Failed to send Telegram message: {e}")
            return False
    
    # For other channels (WhatsApp, LINE), messages are just stored
    # Actual delivery happens via their respective APIs/webhooks
    return True
```

## 4. Integration with Chat Automation

```python
# Modify src/ae/chat_automation.py

# In run_due_chat_automations function, add delivery:

async def run_due_chat_automations_async(
    db_path: str,
    *,
    now: Optional[datetime] = None,
    limit: int = 50
) -> int:
    """Async version that delivers messages."""
    from .chat_message_delivery import deliver_message
    
    now = now or datetime.utcnow()
    due = list_due_automations(db_path, now=now, limit=limit)
    sent = 0
    
    for a in due:
        try:
            body = render_template(db_path, a.template_key, a.context_json)
            
            # Get reply markup if template specifies it
            reply_markup = None
            if a.template_key == "money_board.package_menu":
                # Get packages and create keyboard
                packages = repo.list_packages(db_path, active=True, limit=20)
                from .telegram_bot_client import TelegramBotClient
                bot_client = get_telegram_bot_client(db_path)
                if bot_client:
                    reply_markup = bot_client.create_package_menu_keyboard(
                        [p.model_dump() for p in packages]
                    )
            
            # Deliver message
            delivered = await deliver_message(
                db_path,
                a.conversation_id,
                body,
                reply_markup=reply_markup
            )
            
            if delivered:
                # Insert message record
                insert_message(
                    db_path,
                    conversation_id=a.conversation_id,
                    direction="outbound",
                    text=body,
                    payload_json={"template_key": a.template_key, "reply_markup": reply_markup}
                )
                
                # Emit event
                EventBus.emit_topic(...)
                mark_sent(db_path, a.automation_id, now)
                sent += 1
        except Exception as e:
            # Handle error
            pass
    
    return sent
```

## 5. Moneyboard Integration Example

```python
# Modify src/ae/console_routes_money_board.py

# In send_package_menu function:

@admin_router.post("/{lead_id}/send-package-menu")
async def send_package_menu(lead_id: int, request: Request, _=Depends(_admin)):
    """Send package menu template to lead."""
    db_path = _resolve_db_path(request.query_params.get("db"))
    
    # Get active packages
    packages = repo.list_packages(db_path, active=True, limit=20)
    
    # Get conversation
    conversations = list_conversations(db_path, lead_id=str(lead_id), limit=1)
    if not conversations:
        raise HTTPException(status_code=404, detail="no_conversation_found")
    
    conversation = conversations[0]
    channel = get_chat_channel(db_path, conversation.channel_id)
    
    # Render template
    package_list = "\n".join([
        f"{i+1}. {p.name} - ฿{p.price:.0f} ({p.duration_min} min)"
        for i, p in enumerate(packages)
    ])
    
    message_text = render_template(
        db_path,
        "money_board.package_menu",
        {"package_list": package_list}
    )
    
    # Create inline keyboard if Telegram
    reply_markup = None
    if channel.provider == ChatProvider.telegram:
        bot_client = get_telegram_bot_client(db_path, channel.channel_id)
        if bot_client:
            reply_markup = bot_client.create_package_menu_keyboard(
                [p.model_dump() for p in packages]
            )
    
    # Deliver message
    if channel.provider == ChatProvider.telegram:
        chat_id = conversation.external_thread_id
        if bot_client and chat_id:
            await bot_client.send_message(
                chat_id=str(chat_id),
                text=message_text,
                reply_markup=reply_markup
            )
    
    # Store message
    insert_chat_message(...)
    
    return {"sent": True, "message": message_text}
```

## 6. Deep Link Handling

```python
# In webhook handler, handle /start command with deep link

async def _handle_start_command(db_path: str, conversation, text: str, from_user: Dict):
    """Handle /start command with optional deep link."""
    # Parse: /start lead_123
    parts = text.split()
    lead_id = None
    
    if len(parts) > 1:
        # Deep link: /start lead_123
        lead_id_str = parts[1]
        if lead_id_str.startswith("lead_"):
            lead_id = int(lead_id_str.replace("lead_", ""))
    
    # Link conversation to lead
    if lead_id:
        conversation = get_or_create_conversation(
            db_path,
            conversation_id=conversation.conversation_id,
            channel_id=conversation.channel_id,
            external_thread_id=conversation.external_thread_id,
            lead_id=str(lead_id)
        )
    
    # Send welcome message
    welcome_text = render_template(
        db_path,
        "telegram.welcome",
        {"lead_id": lead_id}
    )
    
    # Send via bot
    bot_client = get_telegram_bot_client(db_path)
    if bot_client:
        await bot_client.send_message(
            chat_id=conversation.external_thread_id,
            text=welcome_text
        )
```

## 7. Configuration Example

```python
# In chat_channels table, store Telegram bot token:

channel = repo.upsert_chat_channel(
    db_path=db_path,
    channel_id='ch_demo1_telegram',
    provider=ChatProvider.telegram,
    handle='@your_bot_username',
    display_name='Demo Plumbing Telegram',
    meta_json={
        'client_id': 'demo1',
        'telegram_bot_token': '123456789:ABCdefGHIjklMNOpqrsTUVwxyz',
        'telegram_chat_id': None  # For group channels
    }
)
```

## 8. Webhook Setup

```bash
# Set webhook URL (one-time setup)
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://yourdomain.com/api/v1/telegram/webhook?db=acq.db"}'

# Optional: Set webhook secret
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://yourdomain.com/api/v1/telegram/webhook?db=acq.db",
    "secret_token": "your_secret_token"
  }'
```

## Notes

1. **Error Handling**: All API calls should have proper error handling and retries
2. **Rate Limiting**: Telegram has rate limits (30 messages/second per chat)
3. **Async**: Use async/await for all Telegram API calls
4. **Logging**: Log all message deliveries and failures
5. **Testing**: Test with test Telegram account before production
6. **Security**: Keep bot tokens secure, use environment variables
