# Telegram Bot Implementation Guide

## Quick Start

This guide provides step-by-step instructions for implementing the lean Telegram bot integration.

## Prerequisites

1. Telegram bot created via @BotFather
2. Bot token obtained
3. Public HTTPS endpoint for webhook

## Implementation Order

### Step 1: Webhook Handler (Day 1)

**File:** `src/ae/console_routes_telegram_webhook.py`

**Purpose:** Receive messages from Telegram

**Key Points:**
- Reuses `get_or_create_conversation()`
- Reuses `insert_message()`
- Reuses `EventBus.emit_topic()`
- ~100 lines of code

**Register in:** `public_api.py`

### Step 2: Delivery Helper (Day 1)

**File:** `src/ae/telegram_delivery.py`

**Purpose:** Send messages via Telegram

**Key Points:**
- Reuses `repo_alerts._send_telegram()`
- Simple wrapper function
- ~50 lines of code

### Step 3: Extend Automation (Day 2)

**File:** `src/ae/chat_automation.py`

**Change:** Add Telegram delivery to `run_due_chat_automations()`

**Lines:** +5-10 lines

### Step 4: Extend Moneyboard API (Day 2)

**File:** `src/ae/console_routes_money_board.py`

**Change:** Add Telegram delivery to `send_template()`

**Lines:** +5-10 lines

### Step 5: Landing Page Deep Link (Day 3)

**File:** `src/ae/adapters/publisher_tailwind_static.py`

**Change:** Add deep link generation in `selectPackage()`

**Lines:** +10 lines

**File:** `src/ae/console_routes_chat_public.py`

**Change:** Enhance Telegram URL generation

**Lines:** +5 lines

## Code Templates

### Webhook Handler Template

```python
from fastapi import APIRouter, Request
from .console_support import _resolve_db_path
from .public_guard import rate_limit_or_429
from .repo_chat_conversations import get_or_create_conversation
from .repo_chat_messages import insert_message
from .repo_chat_channels import list_chat_channels
from .event_bus import EventBus
from .enums import ChatProvider
from datetime import datetime

public_router = APIRouter()

@public_router.post("/v1/telegram/webhook")
async def telegram_webhook(request: Request):
    rate_limit_or_429(request)
    db_path = _resolve_db_path(request.query_params.get("db"))
    
    update = await request.json()
    
    # Find Telegram channel
    channels = list_chat_channels(db_path, provider=ChatProvider.telegram, limit=1)
    if not channels:
        return {"ok": False, "error": "no_telegram_channel"}
    
    channel = channels[0]
    
    # Handle message or callback_query
    if "message" in update:
        await _handle_message(db_path, channel, update["message"])
    elif "callback_query" in update:
        await _handle_callback(db_path, channel, update["callback_query"])
    
    return {"ok": True}

async def _handle_message(db_path: str, channel, message: dict):
    chat_id = str(message["chat"]["id"])
    text = message.get("text", "")
    message_id = str(message["message_id"])
    
    # Get/create conversation (REUSE EXISTING)
    conversation = get_or_create_conversation(
        db_path,
        conversation_id=f"conv_telegram_{chat_id}",
        channel_id=channel.channel_id,
        external_thread_id=str(chat_id),
        meta_json={"telegram_chat_id": chat_id}
    )
    
    # Store message (REUSE EXISTING)
    insert_message(
        db_path,
        conversation_id=conversation.conversation_id,
        direction="inbound",
        text=text,
        external_msg_id=message_id,
        ts=datetime.utcnow()
    )
    
    # Emit event (REUSE EXISTING)
    EventBus.emit_topic(
        db_path,
        topic="op.chat.message_received",
        aggregate_type="chat",
        aggregate_id=conversation.conversation_id,
        payload={
            "conversation_id": conversation.conversation_id,
            "text": text
        }
    )
    
    # Handle /start command with deep link
    if text.startswith("/start"):
        args = text.split()[1:] if len(text.split()) > 1 else []
        if args and args[0].startswith("package_"):
            package_id = args[0].replace("package_", "")
            await _handle_package_deep_link(db_path, conversation, package_id)
```

### Delivery Helper Template

```python
from .repo_chat_channels import get_chat_channel
from .repo_chat_conversations import get_conversation
from .enums import ChatProvider
from .repo_alerts import _send_telegram  # REUSE EXISTING

def send_message(db_path: str, conversation_id: str, text: str) -> bool:
    """Send message via Telegram - reuses existing function."""
    conversation = get_conversation(db_path, conversation_id)
    if not conversation:
        return False
    
    channel = get_chat_channel(db_path, conversation.channel_id)
    if not channel or channel.provider != ChatProvider.telegram:
        return False
    
    # Get bot token from channel config
    bot_token = channel.meta_json.get("telegram_bot_token")
    if not bot_token:
        return False
    
    # Get Telegram chat_id
    chat_id = conversation.external_thread_id
    if not chat_id:
        return False
    
    # REUSE EXISTING FUNCTION
    ok, _ = _send_telegram(bot_token, str(chat_id), text)
    return ok
```

### Extension Template (chat_automation.py)

```python
# In run_due_chat_automations(), add after render_template():
for a in due:
    try:
        body = render_template(db_path, a.template_key, a.context_json)
        
        # NEW: Deliver via Telegram if channel is Telegram
        from .telegram_delivery import send_message
        send_message(db_path, a.conversation_id, body)
        
        # Existing: Store message
        insert_message(...)
        # ... rest unchanged ...
```

## Configuration

### 1. Create Telegram Channel

```python
from ae import repo
from ae.enums import ChatProvider

repo.upsert_chat_channel(
    db_path="acq.db",
    channel_id="ch_demo1_telegram",
    provider=ChatProvider.telegram,
    handle="@your_bot_username",
    display_name="Demo Bot",
    meta_json={
        "client_id": "demo1",
        "telegram_bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
    }
)
```

### 2. Set Webhook URL

```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://yourdomain.com/api/v1/telegram/webhook?db=acq.db"}'
```

### 3. Test Webhook

```bash
# Send test message to bot
# Check logs for webhook receipt
# Verify message stored in database
```

## Testing Checklist

### Phase 1: Webhook
- [ ] Webhook receives messages
- [ ] Messages stored in database
- [ ] Events emitted correctly
- [ ] Conversations created correctly

### Phase 2: Delivery
- [ ] Outbound messages sent via Telegram
- [ ] Automation messages delivered
- [ ] Moneyboard messages delivered
- [ ] Error handling works

### Phase 3: Deep Links
- [ ] Landing page generates deep links
- [ ] Bot handles /start package_xxx
- [ ] Package confirmation works
- [ ] Booking flow completes

## Troubleshooting

### Webhook Not Receiving Messages
- Check webhook URL is set correctly
- Verify HTTPS endpoint is accessible
- Check bot token is correct
- Review Telegram API logs

### Messages Not Delivered
- Verify bot token in channel config
- Check chat_id is stored in conversation
- Review delivery function logs
- Test `_send_telegram()` directly

### Deep Links Not Working
- Verify deep link format: `package_xxx`
- Check conversation creation
- Review webhook handler logs
- Test with manual /start command

## Next Steps

1. **Implement Phase 1** (Webhook) - 1 day
2. **Test Phase 1** - Verify messages received
3. **Implement Phase 2** (Delivery) - 1 day
4. **Test Phase 2** - Verify messages sent
5. **Implement Phase 3** (Deep Links) - 1 day
6. **Test Phase 3** - End-to-end flow
7. **Deploy** - Production rollout

## Estimated Timeline

- **Day 1:** Webhook handler + Delivery helper
- **Day 2:** Extend automation + Moneyboard API
- **Day 3:** Landing page deep links + Testing
- **Total:** 3 days for customer bot

## Optional: Vendor Bot

If implementing vendor bot:
- **Day 4-5:** Vendor bot webhook + Commands
- **Total:** 5 days for both bots

## Support

For questions or issues:
1. Review `TELEGRAM_BOT_LEAN_INTEGRATION.md` for design details
2. Check existing code patterns in `chat_automation.py`
3. Review `repo_alerts.py` for Telegram sending function
4. Test incrementally at each phase
