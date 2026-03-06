# Telegram Bot Lean Integration Design

## Philosophy: Maximize Reuse, Minimize New Code

This design integrates Telegram bot functionality by **extending existing systems** rather than creating new ones. The goal is to add Telegram support with minimal code changes and zero schema changes.

## Key Insight

**Current State:** Messages are stored but not delivered. The system already has:
- ✅ Conversation mapping (`chat_conversations`)
- ✅ Message storage (`chat_messages`)
- ✅ Template system (`chat_templates`)
- ✅ Automation hooks (`chat_automation.py`)
- ✅ Moneyboard API (`console_routes_money_board.py`)
- ✅ Telegram sending function (`repo_alerts._send_telegram`)

**What's Missing:** Actual delivery mechanism for Telegram messages.

## Integration Strategy

### 1. Extend Existing Functions (Not Replace)

Instead of creating new delivery systems, **extend** existing functions to deliver via Telegram when appropriate.

**Files to Modify:**
- `chat_automation.py` - Add Telegram delivery to `run_due_chat_automations()`
- `console_routes_money_board.py` - Add Telegram delivery to `send_template()`
- `console_routes_chat_public.py` - Add deep link support to `_generate_chat_url()`

**New Files (Minimal):**
- `console_routes_telegram_webhook.py` - Webhook handler (~100 lines)
- `telegram_delivery.py` - Delivery helper (~50 lines, reuses `repo_alerts._send_telegram`)

### 2. Reuse Existing Infrastructure

#### Conversation Mapping
```python
# Already exists - just use it!
conversation = get_or_create_conversation(
    db_path,
    conversation_id=f"conv_telegram_{chat_id}",
    channel_id=telegram_channel_id,
    external_thread_id=str(chat_id),  # Store Telegram chat_id here
    meta_json={"telegram_chat_id": chat_id}
)
```

#### Message Storage
```python
# Already exists - just use it!
insert_message(
    db_path,
    conversation_id=conversation_id,
    direction="inbound",  # or "outbound"
    text=text,
    external_msg_id=telegram_message_id
)
```

#### Templates
```python
# Already exists - just use it!
message_text = render_template(db_path, template_key, context)
```

#### Telegram Sending
```python
# Already exists in repo_alerts.py - reuse it!
from .repo_alerts import _send_telegram
```

### 3. Minimal Webhook Handler

**New File:** `src/ae/console_routes_telegram_webhook.py` (~100 lines)

```python
@public_router.post("/v1/telegram/webhook")
async def telegram_webhook(request: Request):
    """Handle Telegram webhook - minimal implementation."""
    # Parse update
    # Find/create conversation
    # Store message (existing function)
    # Emit event (existing function)
    # Done!
```

### 4. Extend Existing Delivery Points

**Modify:** `src/ae/chat_automation.py`

```python
def run_due_chat_automations(db_path: str, *, now: Optional[datetime] = None, limit: int = 50) -> int:
    # ... existing code ...
    for a in due:
        body = render_template(db_path, a.template_key, a.context_json)
        
        # NEW: Deliver via Telegram if channel is Telegram
        conversation = get_conversation(db_path, a.conversation_id)
        if conversation:
            channel = get_chat_channel(db_path, conversation.channel_id)
            if channel and channel.provider == ChatProvider.telegram:
                telegram_delivery.send_message(db_path, conversation, body)
        
        # Existing: Store message
        insert_message(...)
        # ... rest of existing code ...
```

**Modify:** `src/ae/console_routes_money_board.py`

```python
@admin_router.post("/send-template")
def send_template(payload: SendTemplateRequest, request: Request, _=Depends(_admin)):
    # ... existing code ...
    
    # Render template (existing)
    message_text = render_template(db_path, payload.template_key, context)
    
    # NEW: Deliver via Telegram if channel is Telegram
    channel = _find_channel_for_client(db_path, lead.client_id)
    if channel and channel.provider == ChatProvider.telegram:
        telegram_delivery.send_message(db_path, conversation, message_text)
    
    # Existing: Store message
    insert_chat_message(...)
    # ... rest of existing code ...
```

### 5. Landing Page Deep Link (Small Change)

**Modify:** `src/ae/adapters/publisher_tailwind_static.py`

```python
# In selectPackage() function, add:
if (chatChannel && chatChannel.provider === 'telegram') {
  const botUsername = chatChannel.handle.replace('@', '');
  window.location.href = `https://t.me/${botUsername}?start=package_${packageId}`;
  return;
}
// Existing fallback code...
```

**Modify:** `src/ae/console_routes_chat_public.py`

```python
def _generate_chat_url(provider: str, handle: str) -> str:
    # ... existing code ...
    elif provider_lower == "telegram":
        # NEW: Support deep links
        username = handle.replace("@", "")
        return f"https://t.me/{username}"  # Can add ?start=... later
```

## Implementation Plan

### Phase 1: Webhook Handler (1 day)
**New File:** `console_routes_telegram_webhook.py`
- Parse Telegram update
- Find/create conversation using existing functions
- Store message using existing `insert_message()`
- Emit event using existing `EventBus.emit_topic()`

**Lines of Code:** ~100

### Phase 2: Delivery Extension (1 day)
**New File:** `telegram_delivery.py`
- Helper function to send via Telegram
- Reuses `repo_alerts._send_telegram()`

**Modify:** `chat_automation.py`
- Add 5-10 lines to deliver via Telegram

**Modify:** `console_routes_money_board.py`
- Add 5-10 lines to deliver via Telegram

**Lines of Code:** ~70 new + ~20 modified

### Phase 3: Deep Link Support (1 day)
**Modify:** `publisher_tailwind_static.py`
- Add deep link generation (~10 lines)

**Modify:** `console_routes_chat_public.py`
- Enhance Telegram URL generation (~5 lines)

**New:** Webhook handler deep link parsing (~20 lines)

**Lines of Code:** ~35

### Phase 4: Vendor Bot (Optional, 2 days)
**New File:** `console_routes_telegram_vendor.py`
- Separate webhook endpoint for vendor bot
- Reuses existing Moneyboard API endpoints
- Minimal new code

**Lines of Code:** ~150

## Code Structure

### New Files (Minimal)

```
src/ae/
├── console_routes_telegram_webhook.py  (~100 lines)
│   └── Webhook handler, reuses existing functions
│
├── telegram_delivery.py  (~50 lines)
│   └── Delivery helper, reuses repo_alerts._send_telegram
│
└── (Optional) console_routes_telegram_vendor.py  (~150 lines)
    └── Vendor bot, reuses Moneyboard API
```

### Modified Files (Minimal Changes)

```
src/ae/
├── chat_automation.py
│   └── +5-10 lines: Add Telegram delivery
│
├── console_routes_money_board.py
│   └── +5-10 lines: Add Telegram delivery
│
├── adapters/publisher_tailwind_static.py
│   └── +10 lines: Deep link generation
│
└── console_routes_chat_public.py
    └── +5 lines: Enhanced Telegram URL
```

## Key Design Decisions

### 1. No Schema Changes
- Use existing `chat_conversations.external_thread_id` for Telegram chat_id
- Use existing `chat_channels.meta_json` for bot token storage
- Use existing `chat_messages` table

### 2. Reuse Existing Functions
- `get_or_create_conversation()` - Already handles conversation mapping
- `insert_message()` - Already stores messages
- `render_template()` - Already renders templates
- `_send_telegram()` - Already sends Telegram messages
- `EventBus.emit_topic()` - Already emits events

### 3. Minimal New Abstractions
- No new "delivery adapter" layer
- No new "bot framework" wrapper
- Just extend existing functions with Telegram-specific logic

### 4. Backward Compatible
- Existing WhatsApp/LINE flows unchanged
- Telegram is additive, not replacement
- Falls back gracefully if Telegram not configured

## Example: Complete Flow

### Landing Page → Telegram Bot

```javascript
// Landing page (existing code, small addition)
selectPackage(packageId) {
  // ... existing tracking ...
  
  // NEW: Check for Telegram
  if (chatChannel.provider === 'telegram') {
    window.location.href = `https://t.me/${botUsername}?start=package_${packageId}`;
    return;
  }
  
  // Existing fallback
  window.location.href = chatUrl;
}
```

### Telegram Webhook Handler

```python
# NEW FILE: console_routes_telegram_webhook.py
@public_router.post("/v1/telegram/webhook")
async def telegram_webhook(request: Request):
    update = await request.json()
    
    # Find Telegram channel
    channel = find_telegram_channel(db_path)
    
    # Get/create conversation (EXISTING FUNCTION)
    chat_id = str(update["message"]["chat"]["id"])
    conversation = get_or_create_conversation(
        db_path,
        conversation_id=f"conv_telegram_{chat_id}",
        channel_id=channel.channel_id,
        external_thread_id=str(chat_id)
    )
    
    # Store message (EXISTING FUNCTION)
    insert_message(
        db_path,
        conversation_id=conversation.conversation_id,
        direction="inbound",
        text=update["message"]["text"]
    )
    
    # Emit event (EXISTING FUNCTION)
    EventBus.emit_topic(
        db_path,
        topic="op.chat.message_received",
        aggregate_id=conversation.conversation_id,
        payload={"text": update["message"]["text"]}
    )
    
    # Handle deep link if /start command
    if update["message"]["text"].startswith("/start"):
        handle_deep_link(db_path, conversation, update["message"]["text"])
    
    return {"ok": True}
```

### Delivery Extension

```python
# NEW FILE: telegram_delivery.py
def send_message(db_path: str, conversation: ChatConversation, text: str) -> bool:
    """Send message via Telegram - reuses existing function."""
    channel = get_chat_channel(db_path, conversation.channel_id)
    if not channel or channel.provider != ChatProvider.telegram:
        return False
    
    # Get bot token from channel config
    bot_token = channel.meta_json.get("telegram_bot_token")
    if not bot_token:
        return False
    
    # Get Telegram chat_id from conversation
    chat_id = conversation.external_thread_id
    if not chat_id:
        return False
    
    # REUSE EXISTING FUNCTION
    from .repo_alerts import _send_telegram
    ok, _ = _send_telegram(bot_token, str(chat_id), text)
    return ok
```

### Extend Automation Runner

```python
# MODIFY: chat_automation.py (add ~5 lines)
def run_due_chat_automations(db_path: str, *, now: Optional[datetime] = None, limit: int = 50) -> int:
    # ... existing code ...
    for a in due:
        body = render_template(db_path, a.template_key, a.context_json)
        
        # NEW: Deliver via Telegram
        conversation = get_conversation(db_path, a.conversation_id)
        if conversation:
            from .telegram_delivery import send_message
            send_message(db_path, conversation, body)
        
        # Existing: Store message
        insert_message(...)
        # ... rest unchanged ...
```

## Benefits of This Approach

### 1. Minimal Code
- **New code:** ~250 lines total
- **Modified code:** ~30 lines total
- **Total:** ~280 lines

### 2. Low Risk
- Reuses proven, existing functions
- No schema changes
- Backward compatible
- Easy to test incrementally

### 3. Low Technical Debt
- No new abstractions
- No duplicate functionality
- Follows existing patterns
- Easy to maintain

### 4. Fast Implementation
- Phase 1: 1 day (webhook)
- Phase 2: 1 day (delivery)
- Phase 3: 1 day (deep links)
- **Total: 3 days** for customer bot

## Configuration

### Existing Channel Config (No Changes)

```python
# Already works - just add bot token to meta_json
channel = repo.upsert_chat_channel(
    db_path=db_path,
    channel_id='ch_demo1_telegram',
    provider=ChatProvider.telegram,
    handle='@demo1_bot',
    display_name='Demo Bot',
    meta_json={
        'client_id': 'demo1',
        'telegram_bot_token': '123456789:ABC...'  # NEW: Add token
    }
)
```

### Environment Variables (Optional)

```bash
# Optional: Default bot token if not in channel config
TELEGRAM_BOT_TOKEN=123456789:ABC...

# Webhook URL (set via Telegram API)
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/api/v1/telegram/webhook
```

## Testing Strategy

### Unit Tests
- Test webhook handler parsing
- Test delivery function
- Test deep link parsing

### Integration Tests
- Test full flow: landing page → bot → booking
- Test existing flows still work
- Test backward compatibility

### Manual Testing
- Test with real Telegram bot
- Test deep links
- Test message delivery

## Migration Path

### Step 1: Add Webhook (No Breaking Changes)
- Deploy webhook handler
- Configure webhook URL
- Test inbound messages

### Step 2: Add Delivery (No Breaking Changes)
- Deploy delivery extension
- Test outbound messages
- Verify existing flows still work

### Step 3: Add Deep Links (No Breaking Changes)
- Deploy landing page changes
- Test deep link flow
- Monitor usage

### Step 4: Optional Vendor Bot
- Deploy vendor bot
- Configure vendor channels
- Test vendor workflow

## Summary

This lean integration approach:
- ✅ **Reuses** existing infrastructure (conversations, messages, templates, events)
- ✅ **Extends** existing functions (minimal changes)
- ✅ **Adds** minimal new code (~280 lines total)
- ✅ **Maintains** backward compatibility
- ✅ **Follows** existing patterns
- ✅ **Reduces** technical debt

**Result:** Fast, low-risk, maintainable Telegram bot integration that fits seamlessly into the existing architecture.
