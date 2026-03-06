# Telegram Bot Integration with Moneyboard - Investigation

## Executive Summary

This document investigates the opportunity to integrate a Telegram chatbot into the Moneyboard system, enabling two-way communication between customers and businesses through Telegram while leveraging existing Moneyboard workflows and automation.

## Current State Analysis

### ✅ What Already Exists

1. **Telegram Provider Support**
   - `ChatProvider.telegram` enum exists
   - URL generation for Telegram (`https://t.me/{username}`)
   - Script to create Telegram channels (`create_telegram_channel.py`)

2. **Telegram Bot Token Infrastructure**
   - Telegram bot token storage in alert notification config
   - One-way Telegram messaging for admin alerts (`repo_alerts.py`)
   - Settings UI for configuring Telegram bot token

3. **Chat Channel Registry**
   - Database table: `chat_channels`
   - Supports multiple providers (WhatsApp, LINE, Telegram, SMS, etc.)
   - Links channels to clients via `meta_json.client_id`

4. **Chat Automation System**
   - Template-based messaging (`chat_templates.py`)
   - Event-driven automation hooks (`chat_automation.py`)
   - Scheduled message delivery (`chat_automations` table)
   - Moneyboard-specific templates:
     - `money_board.package_menu`
     - `money_board.time_window_request`
     - `money_board.deposit_request`
     - `money_board.deposit_reminder`
     - `money_board.service_reminder_24h`
     - `money_board.service_reminder_2h`
     - `money_board.review_request`

5. **Moneyboard API**
   - `/api/money-board` - Get board data
   - `/api/money-board/{lead_id}/send-package-menu` - Send package menu
   - `/api/money-board/{request_id}/set-time-window` - Set time window
   - `/api/money-board/{request_id}/request-deposit` - Request deposit
   - `/api/money-board/{intent_id}/mark-paid` - Mark payment
   - `/api/money-board/{request_id}/mark-completed` - Mark completed
   - `/api/money-board/{request_id}/close` - Close booking

6. **Conversation & Message Storage**
   - `chat_conversations` table - Maps external threads to leads/bookings
   - `chat_messages` table - Stores all messages (inbound/outbound)
   - Message insertion API exists

### ❌ What's Missing

1. **Telegram Bot Webhook Handler**
   - No endpoint to receive Telegram webhook updates
   - No inbound message processing from Telegram

2. **Telegram Bot API Integration**
   - No code to actually send messages via Telegram Bot API
   - Messages are stored but not delivered to Telegram

3. **Telegram Chat ID Mapping**
   - No mapping between Telegram `chat_id` and system `conversation_id`
   - No way to identify which Telegram user corresponds to which lead

4. **Interactive Telegram Features**
   - No inline keyboards/buttons for package selection
   - No callback query handling for user interactions
   - No command handlers (`/start`, `/help`, etc.)

## Integration Opportunities

### 1. Two-Way Telegram Communication

**Current Flow (WhatsApp/LINE):**
```
Landing Page → Click "Get Quote" → Redirect to WhatsApp/LINE URL → Manual conversation
```

**Proposed Flow (Telegram Bot):**
```
Landing Page → Click "Get Quote" → Redirect to Telegram bot → Automated conversation
```

**Benefits:**
- Customers can interact directly in Telegram without leaving the app
- Automated responses can guide customers through booking flow
- No need to manually handle each conversation

### 2. Moneyboard Actions via Telegram

**Use Cases:**

1. **Package Selection**
   - Customer clicks "Get Quote" → Bot sends package menu
   - Customer selects package via inline keyboard
   - Bot confirms selection and moves to next step

2. **Time Window Selection**
   - Bot asks for preferred time window
   - Customer responds with time preference
   - Bot updates booking request in Moneyboard

3. **Deposit Request**
   - Bot sends deposit request with payment link
   - Customer can confirm payment via button
   - Bot updates payment status in Moneyboard

4. **Service Reminders**
   - Automated 24h and 2h reminders before service
   - Sent via Telegram instead of SMS/email
   - Higher engagement rates

5. **Review Requests**
   - After service completion, bot requests review
   - Customer can leave feedback directly in Telegram

### 3. Real-Time Moneyboard Updates

**Opportunity:**
- When operator performs action in Moneyboard UI, bot sends message to customer
- Customer receives instant notifications about booking status
- Reduces need for manual follow-up calls

## Technical Approach

### Architecture Overview

```
┌─────────────────┐
│ Telegram Server │
│  (Webhook)      │
└────────┬────────┘
         │ POST /api/v1/telegram/webhook
         ▼
┌─────────────────────────────────────┐
│ Telegram Webhook Handler             │
│ - Validate webhook secret            │
│ - Parse Telegram Update              │
│ - Map chat_id → conversation_id      │
│ - Insert inbound message             │
│ - Emit op.chat.message_received     │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Chat Automation Engine               │
│ - Trigger automated responses        │
│ - Render templates                   │
│ - Schedule follow-ups                │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Telegram Bot API Client              │
│ - Send messages                     │
│ - Send inline keyboards              │
│ - Handle callback queries            │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Moneyboard API                       │
│ - Update booking status              │
│ - Create payment intents             │
│ - Trigger workflows                  │
└─────────────────────────────────────┘
```

### Implementation Components

#### 1. Telegram Webhook Endpoint

**Location:** `src/ae/console_routes_telegram_webhook.py`

**Responsibilities:**
- Receive POST requests from Telegram
- Validate webhook secret (optional but recommended)
- Parse Telegram Update object
- Extract message/callback data
- Map Telegram `chat_id` to system `conversation_id`
- Insert inbound message
- Emit `op.chat.message_received` event

**Example Structure:**
```python
@public_router.post("/v1/telegram/webhook")
async def telegram_webhook(request: Request):
    # Verify webhook secret if configured
    # Parse Telegram Update
    # Handle message or callback_query
    # Map chat_id to conversation_id
    # Insert message and emit event
```

#### 2. Telegram Bot API Client

**Location:** `src/ae/telegram_bot_client.py`

**Responsibilities:**
- Send text messages
- Send messages with inline keyboards
- Handle callback queries
- Get chat information
- Error handling and retries

**Dependencies:**
- `python-telegram-bot` library (recommended)
- Or `httpx`/`requests` for direct API calls

#### 3. Message Delivery Integration

**Location:** `src/ae/chat_message_delivery.py`

**Responsibilities:**
- Intercept outbound messages from chat automation
- Check if channel is Telegram
- Deliver via Telegram Bot API instead of just storing
- Handle delivery failures

**Integration Points:**
- Hook into `chat_automation.py` `run_due_chat_automations()`
- Hook into `console_routes_money_board.py` `send_template()`

#### 4. Chat ID Mapping

**Strategy:**
- Store Telegram `chat_id` in `chat_conversations.external_thread_id`
- When Telegram webhook receives message, lookup by `chat_id`
- If not found, create new conversation linked to lead (if identifiable)

**Challenges:**
- How to link Telegram user to lead initially?
  - Option A: Include lead_id in Telegram bot deep link (`t.me/bot?start=lead_123`)
  - Option B: Ask customer to provide phone/email to link
  - Option C: Use phone number matching if available

#### 5. Inline Keyboard Support

**Use Cases:**
- Package selection buttons
- Time slot selection
- Payment confirmation
- Booking status checks

**Implementation:**
- Extend `chat_templates.py` to support Telegram-specific formatting
- Add keyboard markup to message payload
- Handle callback queries in webhook handler

### Database Schema Changes

**No changes required** - existing schema supports this:
- `chat_channels` - Already supports Telegram provider
- `chat_conversations` - Can store Telegram chat_id in `external_thread_id`
- `chat_messages` - Already stores messages with `external_msg_id`
- `chat_automations` - Already supports scheduled messages

### Configuration

**New Environment Variables:**
```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_WEBHOOK_SECRET=optional_secret_for_webhook_validation
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/api/v1/telegram/webhook

# Per-channel configuration (stored in chat_channels.meta_json)
{
  "client_id": "demo1",
  "telegram_bot_token": "optional_override_token",
  "telegram_chat_id": "for_group_channels"
}
```

## Implementation Phases

### Phase 1: Basic Webhook & Message Delivery (MVP)

**Goals:**
- Receive Telegram webhook updates
- Store inbound messages
- Send outbound messages via Telegram Bot API
- Basic chat_id to conversation_id mapping

**Deliverables:**
1. Telegram webhook endpoint
2. Telegram Bot API client
3. Message delivery integration
4. Basic conversation mapping

**Estimated Effort:** 2-3 days

### Phase 2: Moneyboard Integration

**Goals:**
- Send package menus via Telegram
- Handle package selection via inline keyboards
- Update booking requests from Telegram interactions
- Send deposit requests with payment links

**Deliverables:**
1. Inline keyboard support
2. Callback query handling
3. Moneyboard action integration
4. Template enhancements for Telegram

**Estimated Effort:** 2-3 days

### Phase 3: Advanced Features

**Goals:**
- Deep linking (t.me/bot?start=lead_123)
- Command handlers (/start, /help, /status)
- Rich media support (images, documents)
- Group chat support
- Multi-language support

**Deliverables:**
1. Deep link handling
2. Command system
3. Media support
4. Enhanced UX

**Estimated Effort:** 3-4 days

## Benefits

### For Customers
- ✅ Instant responses via Telegram
- ✅ No need to switch apps
- ✅ Interactive buttons for easy selection
- ✅ Push notifications for updates
- ✅ Familiar interface (Telegram)

### For Operators
- ✅ Automated booking flow
- ✅ Reduced manual follow-up
- ✅ All conversations in one place (Moneyboard)
- ✅ Integration with existing workflows
- ✅ Better customer engagement

### For Business
- ✅ Higher conversion rates (frictionless booking)
- ✅ Reduced support burden
- ✅ Better customer experience
- ✅ Scalable automation
- ✅ Multi-channel support (Telegram + WhatsApp + LINE)

## Risks & Considerations

### Technical Risks
1. **Webhook Reliability**
   - Telegram webhooks can fail
   - Need retry mechanism
   - Consider polling as fallback

2. **Rate Limiting**
   - Telegram Bot API has rate limits
   - Need to handle gracefully
   - Queue messages if needed

3. **Chat ID Mapping**
   - Linking Telegram users to leads can be tricky
   - Need clear strategy for initial mapping
   - Consider phone number matching

### Operational Risks
1. **Bot Token Security**
   - Bot tokens must be kept secret
   - Use environment variables
   - Rotate tokens if compromised

2. **Spam/Abuse**
   - Telegram bots can receive spam
   - Implement rate limiting
   - Block abusive users

3. **Multi-Channel Complexity**
   - Customers might use multiple channels
   - Need to handle channel switching
   - Maintain conversation continuity

## Dependencies

### Required Libraries
```python
# Option 1: python-telegram-bot (recommended)
python-telegram-bot>=20.0

# Option 2: Direct API calls (lighter weight)
httpx>=0.24.0  # or requests>=2.31.0
```

### Infrastructure
- Public HTTPS endpoint for webhook
- Telegram Bot created via @BotFather
- Bot token obtained and configured

## Next Steps

1. **Decision Point:** Approve integration approach
2. **Setup:** Create Telegram bot via @BotFather
3. **Phase 1 Implementation:** Basic webhook and message delivery
4. **Testing:** Test with test Telegram account
5. **Phase 2 Implementation:** Moneyboard integration
6. **Pilot:** Test with one client
7. **Rollout:** Deploy to production

## References

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [python-telegram-bot Documentation](https://python-telegram-bot.org/)
- Existing LINE integration: `docs/LINE_INTEGRATION.md`
- Chat automation: `src/ae/chat_automation.py`
- Moneyboard API: `src/ae/console_routes_money_board.py`
