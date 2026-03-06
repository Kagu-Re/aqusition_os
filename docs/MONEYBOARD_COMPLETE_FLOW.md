# Moneyboard Complete Flow - Implementation Audit Document

**Version:** 1.0  
**Date:** February 7, 2026  
**Purpose:** Comprehensive documentation of current Moneyboard implementation for audit purposes

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Database Schema](#database-schema)
4. [Landing Page Flow](#landing-page-flow)
5. [Customer Bot Flow](#customer-bot-flow)
6. [Vendor Bot Flow](#vendor-bot-flow)
7. [Moneyboard API](#moneyboard-api)
8. [Backend Modules](#backend-modules)
9. [Event System](#event-system)
10. [Chat Automation](#chat-automation)
11. [Complete Flow Diagrams](#complete-flow-diagrams)

---

## System Overview

The Moneyboard system manages the complete booking lifecycle from initial lead capture through service delivery. It integrates:

- **Landing Pages** - Customer-facing pages that capture leads
- **Customer Telegram Bot** - Automated booking assistant for customers
- **Vendor Telegram Bot** - Management interface for vendors/operators
- **Moneyboard UI** - Web-based dashboard for operators
- **Moneyboard API** - RESTful API for booking management

### Key Components

- **Lead Intake** - Captures customer information from landing pages
- **Booking Requests** - Tracks booking lifecycle (requested → confirmed → completed)
- **Payment Intents** - Manages payment requests and status
- **Chat Conversations** - Links Telegram chats to leads/bookings
- **Chat Automation** - Automated messaging based on booking events

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Landing Page (Static HTML)                   │
│  - Form submission → POST /lead                                │
│  - Package selection → Redirect to Telegram bot                │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Public API Layer                             │
│  - POST /lead (lead intake)                                     │
│  - GET /v1/chat/channel (get chat URL)                          │
│  - POST /v1/telegram/webhook (Telegram webhook)                 │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Database (SQLite)                             │
│  - lead_intake                                                   │
│  - booking_requests                                             │
│  - payment_intents                                              │
│  - chat_conversations                                           │
│  - chat_messages                                                │
│  - chat_automations                                             │
└────────────────────┬────────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌──────────────────┐    ┌──────────────────┐
│ Customer Bot     │    │ Vendor Bot        │
│ (Telegram)       │    │ (Telegram)        │
│                  │    │                   │
│ - /start         │    │ - /bookings       │
│ - Package select │    │ - /confirm        │
│ - Time window    │    │ - /paid           │
│ - Booking create │    │ - /complete       │
└──────────────────┘    └──────────────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Moneyboard API                                │
│  - GET /api/money-board (get board data)                        │
│  - POST /api/money-board/{lead_id}/send-package-menu            │
│  - POST /api/money-board/{request_id}/set-time-window           │
│  - POST /api/money-board/{request_id}/request-deposit           │
│  - POST /api/money-board/{intent_id}/mark-paid                  │
│  - POST /api/money-board/{request_id}/mark-completed            │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Moneyboard UI                                 │
│  - Kanban board view                                            │
│  - Status columns: new → package_selected → ... → closed       │
│  - Operator actions via UI                                      │
└─────────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

```
Landing Page
    │
    ├─> Form Submit → POST /lead → Lead Created
    │
    └─> Package Click → Telegram Deep Link → Customer Bot
            │
            ├─> /start package_xxx → Package Confirmed
            │
            ├─> Time Window Selection → Booking Request Created
            │
            └─> Vendor Bot Notified → /bookings shows new booking
                    │
                    ├─> /confirm → Booking Confirmed
                    │
                    ├─> /paid → Payment Marked Paid → Booking Auto-Confirmed
                    │
                    └─> /complete → Booking Completed
```

---

## Database Schema

### Core Tables

#### `lead_intake`
Stores initial customer leads from landing pages.

**Schema:**
```sql
CREATE TABLE lead_intake (
    lead_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    source TEXT,
    page_id TEXT,
    client_id TEXT,
    name TEXT,
    phone TEXT,
    email TEXT,
    message TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    utm_term TEXT,
    utm_content TEXT,
    referrer TEXT,
    user_agent TEXT,
    ip_hint TEXT,
    spam_score INTEGER DEFAULT 0,
    is_spam INTEGER DEFAULT 0,
    status TEXT DEFAULT 'new',
    booking_status TEXT DEFAULT 'none',
    booking_value REAL,
    booking_currency TEXT,
    booking_ts TEXT,
    meta_json TEXT NOT NULL DEFAULT '{}'
);
```

**Key Fields:**
- `lead_id` - Primary key, auto-increment
- `client_id` - Links to client
- `status` - Lead status: "new", "spam", "contacted", etc.
- `booking_status` - Booking status: "none", "booked", "confirmed", "completed"
- `meta_json` - Flexible JSON storage (includes `telegram_chat_id`, `telegram_username`)

**Indexes:**
- Index on `client_id`
- Index on `status`
- Index on `booking_status`

#### `booking_requests`
Tracks booking lifecycle.

**Schema:**
```sql
CREATE TABLE booking_requests (
    request_id TEXT PRIMARY KEY,
    lead_id INTEGER NOT NULL,
    package_id TEXT NOT NULL,
    preferred_window TEXT,  -- "morning" | "afternoon" | "evening"
    location TEXT,
    status TEXT NOT NULL DEFAULT 'requested',
    meta_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(lead_id) REFERENCES lead_intake(lead_id)
);
```

**Status Flow:**
```
requested → deposit_requested → confirmed → completed → closed
```

**Key Fields:**
- `request_id` - Unique booking ID (format: `br_telegram_{chat_id}_{timestamp}`)
- `lead_id` - Foreign key to `lead_intake`
- `package_id` - Foreign key to `service_packages`
- `preferred_window` - Time preference: "Morning (9am-12pm)", "Afternoon (12pm-5pm)", "Evening (5pm-9pm)"
- `status` - Current booking status
- `meta_json` - Stores `telegram_chat_id`, `telegram_username`, `source: "telegram_bot"`

**Indexes:**
- Index on `lead_id`
- Index on `status`
- Index on `created_at`

#### `payment_intents`
Manages payment requests.

**Schema:**
```sql
CREATE TABLE payment_intents (
    intent_id TEXT PRIMARY KEY,
    lead_id INTEGER NOT NULL,
    booking_request_id TEXT NOT NULL,
    amount REAL NOT NULL,
    method TEXT NOT NULL,  -- "promptpay" | "stripe" | "bank"
    status TEXT NOT NULL DEFAULT 'requested',  -- "requested" | "paid"
    payment_link TEXT,
    meta_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(lead_id) REFERENCES lead_intake(lead_id),
    FOREIGN KEY(booking_request_id) REFERENCES booking_requests(request_id)
);
```

**Key Fields:**
- `intent_id` - Unique payment ID (format: `pi_{request_id}_{timestamp}`)
- `booking_request_id` - Foreign key to `booking_requests`
- `amount` - Payment amount
- `method` - Payment method
- `status` - Payment status: "requested" → "paid"

**Indexes:**
- Index on `booking_request_id`
- Index on `status`

#### `chat_channels`
Registry of chat channels (Telegram, WhatsApp, LINE, etc.).

**Schema:**
```sql
CREATE TABLE chat_channels (
    channel_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,  -- "telegram" | "whatsapp" | "line" | "sms"
    handle TEXT NOT NULL,  -- Telegram username, phone number, etc.
    display_name TEXT,
    meta_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
```

**Key Fields:**
- `channel_id` - Unique channel ID (e.g., `ch_demo1_telegram`, `ch_vendor_telegram`)
- `provider` - Chat provider type
- `handle` - Channel handle (e.g., `@massage_thaibot`, `@vendorthaibot`)
- `meta_json` - Stores:
  - `client_id` - Links channel to client
  - `telegram_bot_token` - Bot token for Telegram channels
  - `bot_type` - "vendor" for vendor bot, missing/null for customer bot
  - `vendor_chat_id` - Telegram chat ID for vendor notifications

**Indexes:**
- Index on `provider, handle`

#### `chat_conversations`
Maps external chat threads to leads/bookings.

**Schema:**
```sql
CREATE TABLE chat_conversations (
    conversation_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    external_thread_id TEXT,  -- Telegram chat_id, WhatsApp thread ID, etc.
    lead_id TEXT,
    booking_id TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    meta_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(channel_id) REFERENCES chat_channels(channel_id)
);
```

**Key Fields:**
- `conversation_id` - Unique conversation ID (format: `conv_telegram_{chat_id}`)
- `channel_id` - Foreign key to `chat_channels`
- `external_thread_id` - External chat ID (Telegram `chat_id`)
- `lead_id` - Links conversation to lead
- `meta_json` - Stores:
  - `telegram_chat_id` - Telegram chat ID
  - `telegram_username` - Telegram username
  - `pending_package_id` - Package being selected
  - `booking_state` - Current booking state: "awaiting_time_window"
  - `timeslot_list` - Available timeslots
  - `package_list` - Available packages

**Indexes:**
- Index on `channel_id, external_thread_id`
- Index on `lead_id`

#### `chat_messages`
Stores all chat messages (inbound/outbound).

**Schema:**
```sql
CREATE TABLE chat_messages (
    message_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    direction TEXT NOT NULL,  -- "inbound" | "outbound"
    ts TEXT NOT NULL,
    external_msg_id TEXT,  -- Telegram message_id
    text TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(conversation_id) REFERENCES chat_conversations(conversation_id)
);
```

**Key Fields:**
- `message_id` - Unique message ID
- `conversation_id` - Foreign key to `chat_conversations`
- `direction` - Message direction
- `external_msg_id` - External message ID (Telegram `message_id`)
- `text` - Message text
- `payload_json` - Full message payload (includes Telegram message object)

**Indexes:**
- Index on `conversation_id, ts`

#### `chat_automations`
Scheduled automated messages.

**Schema:**
```sql
CREATE TABLE chat_automations (
    automation_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    template_key TEXT NOT NULL,
    due_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- "pending" | "sent" | "cancelled"
    context_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    sent_at TEXT,
    FOREIGN KEY(conversation_id) REFERENCES chat_conversations(conversation_id)
);
```

**Key Fields:**
- `automation_id` - Unique automation ID
- `conversation_id` - Foreign key to `chat_conversations`
- `template_key` - Template to render (e.g., `money_board.service_reminder_24h`)
- `due_at` - When to send (ISO timestamp)
- `status` - Automation status
- `context_json` - Template context variables

**Indexes:**
- Index on `status, due_at`

#### `service_packages`
Service packages available for booking.

**Schema:**
```sql
CREATE TABLE service_packages (
    package_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    duration_min INTEGER NOT NULL,
    addons TEXT NOT NULL DEFAULT '[]',  -- JSON array
    active INTEGER NOT NULL DEFAULT 1,
    meta_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(client_id) REFERENCES clients(client_id)
);
```

**Key Fields:**
- `package_id` - Unique package ID
- `client_id` - Foreign key to `clients`
- `name` - Package name
- `price` - Package price
- `duration_min` - Duration in minutes
- `active` - Whether package is active (1 = active, 0 = inactive)
- `meta_json` - Package metadata (e.g., `max_capacity` for availability)

**Indexes:**
- Index on `client_id, active`

---

## Landing Page Flow

### 1. Page Load

**File:** `src/ae/adapters/publisher_tailwind_static.py`

**Process:**
1. Landing page loads with embedded JavaScript
2. JavaScript fetches chat channel info:
   ```javascript
   fetch(API_BASE + '/v1/chat/channel?client_id=' + CLIENT_ID)
   ```
3. Response includes:
   - `channel_id`
   - `provider` (e.g., "telegram")
   - `handle` (e.g., "@massage_thaibot")
   - `chat_url` (e.g., "https://t.me/massage_thaibot")

### 2. Form Submission

**Endpoint:** `POST /lead`

**File:** `src/ae/console_routes_leads.py`

**Request Payload:**
```json
{
  "source": "landing_page",
  "page_id": "p1",
  "client_id": "demo1",
  "name": "John Doe",
  "phone": "+1234567890",
  "email": "john@example.com",
  "message": "Interested in booking",
  "utm": {
    "utm_source": "google",
    "utm_medium": "cpc",
    "utm_campaign": "massage_ads"
  }
}
```

**Process:**
1. **Spam Detection:**
   - Honeypot field check
   - Spam score calculation (`score_lead_spam()`)
   - Threshold: score >= 60 = spam

2. **Lead Creation:**
   ```python
   lead_id, spam = service.intake_lead(
       db_path,
       source=payload.source,
       page_id=payload.page_id,
       client_id=payload.client_id,
       name=payload.name,
       phone=payload.phone,
       email=payload.email,
       message=payload.message,
       utm=payload.utm,
       referrer=ref,
       user_agent=ua,
       ip_hint=ip_hint,
   )
   ```

3. **Database Insert:**
   - Insert into `lead_intake` table
   - Set `status = "new"` (or `"spam"` if detected)
   - Store UTM parameters
   - Store metadata (referrer, user agent, IP hint)

4. **Activity Log:**
   - Append activity log entry
   - Emit `op.lead.created` event (if not spam)

**Response:**
```json
{
  "ok": true,
  "lead_id": 123,
  "spam": {
    "score": 10,
    "is_spam": false,
    "reasons": []
  }
}
```

### 3. Package Selection & Deep Link

**File:** `src/ae/adapters/publisher_tailwind_static.py`

**Process:**
1. User clicks package on landing page
2. JavaScript tracks event: `trackEvent('call_click')`
3. Creates lead (if not already created):
   ```javascript
   fetch(API_BASE + '/lead', {
     method: 'POST',
     body: JSON.stringify({
       source: 'landing_page',
       page_id: PAGE_ID,
       client_id: CLIENT_ID,
       message: 'Booking request from landing page',
       utm: utmParams
     })
   })
   ```

4. **Telegram Deep Link:**
   - If channel provider is "telegram":
     ```javascript
     const botUsername = chatChannel.handle.replace('@', '');
     window.location.href = `https://t.me/${botUsername}?start=package_${packageId}`;
     ```
   - Deep link format: `t.me/bot?start=package_{package_id}`

5. **Fallback (Non-Telegram):**
   - Redirect to `chat_url` (WhatsApp/LINE URL)

---

## Customer Bot Flow

### Implementation Files

- **Main Handler:** `src/ae/telegram_polling.py`
- **Delivery:** `src/ae/telegram_delivery.py`
- **State Management:** `src/ae/telegram_state.py`
- **Webhook Handler:** `src/ae/console_routes_telegram_webhook.py`

### Bot Initialization

**File:** `src/ae/local_dev_server.py` or `src/ae/telegram_polling.py`

**Process:**
1. Find Telegram channel with `bot_type != "vendor"` and `telegram_bot_token`
2. Create `TelegramPollingClient` instance
3. Start polling loop:
   ```python
   client = TelegramPollingClient(bot_token, db_path, client_id=client_id)
   await client.poll_loop()
   ```

**Polling:**
- Calls `getUpdates` API every 10 seconds
- Processes messages and callback queries
- Uses distributed state manager for deduplication

### 1. `/start` Command (Deep Link)

**Handler:** `handle_message()` → `/start` detection

**Process:**
1. **Lock Acquisition:**
   - Acquire distributed lock for chat_id (prevents concurrent processing)
   - Check cooldown (3 seconds between `/start` commands)

2. **Deep Link Parsing:**
   ```python
   args = text.split()[1:]  # "/start package_pkg123"
   deep_link_param = args[0] if args and args[0].startswith("package_") else None
   ```

3. **Existing Booking Cancellation:**
   - Get or create lead from Telegram chat_id
   - Find active bookings for lead
   - Cancel all active bookings (status → "closed")
   - Notify user: "🔄 Replacing your existing booking..."

4. **Package Deep Link Handling:**
   ```python
   if deep_link_param:
       package_id = deep_link_param.replace("package_", "")
       await self.handle_package_deep_link(conversation, channel, package_id)
   ```

5. **Package Confirmation:**
   - Fetch package from database (with caching)
   - Store `pending_package_id` in conversation meta
   - Send confirmation message:
     ```
     ✅ Package Selected!
     
     📦 Thai Traditional Massage
     💰 ฿500
     ⏱️ 60 minutes
     
     Confirm this package?
     Reply with "yes" to continue or "no" to choose a different package.
     ```

### 2. Package Confirmation (`yes`)

**Handler:** `handle_package_confirmation()`

**Process:**
1. Get `pending_package_id` from conversation meta
2. Fetch package details
3. Calculate availability for each timeslot:
   ```python
   availability = _calculate_availability_for_package(
       db_path,
       package_id,
       package.meta_json or {}
   )
   ```

4. Build timeslot list:
   - Morning (9am-12pm)
   - Afternoon (12pm-5pm)
   - Evening (5pm-9pm)

5. Send timeslot selection message:
   ```
   ✅ Great! You've confirmed:
   
   📦 Thai Traditional Massage
   💰 ฿500
   ⏱️ 60 minutes
   
   ⏰ When would you prefer your appointment?
   
   Please reply with your preferred time window:
   • 1. Morning (9am-12pm) - 5 slots available
   • 2. Afternoon (12pm-5pm) - 3 slots available
   • 3. Evening (5pm-9pm) - 2 slots available
   ```

6. Update conversation state:
   ```python
   conversation_meta["booking_state"] = "awaiting_time_window"
   conversation_meta["timeslot_list"] = timeslot_list
   ```

### 3. Time Window Selection

**Handler:** `handle_timeslot_selection()`

**Process:**
1. **Input Normalization:**
   - Accept: "morning", "afternoon", "evening"
   - Accept: "1", "2", "3"
   - Accept: "Morning (9am-12pm)" (from timeslot_list)

2. **Duplicate Check:**
   - Check for recent booking (within 30 seconds):
     ```python
     existing_booking = get_recent_booking_request(
         db_path,
         lead_id=lead_id,
         package_id=package_id,
         preferred_window=normalized_timeslot,
         within_seconds=30
     )
     ```
   - If duplicate found, return existing booking message

3. **Cooldown Check:**
   - Check booking creation cooldown (10 seconds per chat_id)
   - Prevent rapid duplicate bookings

4. **Lead Creation/Retrieval:**
   ```python
   lead_id = await self._get_or_create_lead_from_telegram(
       chat_id, username, client_id
   )
   ```
   - Uses indexed lookup on `telegram_chat_id` column
   - Creates lead if not exists

5. **Booking Request Creation:**
   ```python
   request_id = f"br_telegram_{chat_id}_{int(time.time() * 1000)}"
   
   booking = BookingRequest(
       request_id=request_id,
       lead_id=lead_id,
       package_id=package_id,
       preferred_window=normalized_timeslot,
       status="requested",
       meta_json={
           "telegram_chat_id": chat_id,
           "telegram_username": username,
           "source": "telegram_bot"
       },
       created_at=datetime.now(timezone.utc),
       updated_at=datetime.now(timezone.utc)
   )
   
   created_booking = create_booking_request(db_path, booking)
   ```

6. **Vendor Notification:**
   ```python
   await self.notify_vendor_bot(created_booking, lead_id)
   ```
   - Finds vendor bot channel (`bot_type == "vendor"`)
   - Sends notification to vendor chat_id:
     ```
     🔔 New Booking Request
     
     📋 Booking ID: br_telegram_123_1234567890
     📦 Package: Thai Traditional Massage
     👤 Customer: John Doe (@johndoe)
     ⏰ Preferred time: Morning (9am-12pm)
     
     To confirm this booking, reply:
     /confirm br_telegram_123_1234567890
     ```

7. **Customer Confirmation:**
   ```
   ✅ Your booking request has been created!
   
   📋 Booking ID: br_telegram_123_1234567890
   📦 Package: Thai Traditional Massage
   ⏰ Preferred time: Morning (9am-12pm)
   
   We'll confirm your appointment shortly. You'll receive a notification once it's confirmed.
   ```

8. **Clear Conversation State:**
   - Remove `pending_package_id`, `booking_state`, `timeslot_list` from meta

### 4. Package Selection (Manual)

**Handler:** `handle_package_selection()` (when user says "no")

**Process:**
1. Fetch active packages for client
2. Build numbered list:
   ```
   📦 Here are our available packages:
   
   1. Thai Traditional Massage
      💰 ฿500 | ⏱️ 60 min
   
   2. Aromatherapy Massage
      💰 ฿700 | ⏱️ 90 min
   
   Please reply with the number (1, 2, 3, etc.) to select a package.
   ```
3. Store `package_list` in conversation meta

### 5. Package Number Selection

**Handler:** `handle_package_number_selection()`

**Process:**
1. Get `package_list` from conversation meta
2. Find package by number
3. Store `pending_package_id` in meta
4. Send confirmation message (same as deep link confirmation)

### State Management

**File:** `src/ae/telegram_state.py`

**Features:**
- **Message Deduplication:** Tracks processed messages (Redis-backed or in-memory)
- **Start Command Cooldown:** Prevents duplicate `/start` processing (3-second cooldown)
- **Deep Link Deduplication:** Prevents duplicate deep link processing (5-second cooldown)
- **Booking Creation Cooldown:** Prevents rapid duplicate bookings (10-second cooldown)
- **Distributed Locks:** Redis-backed locks for concurrent processing prevention

**Implementation:**
- Uses Redis if `AE_REDIS_URL` is set
- Falls back to in-memory state for single-instance deployments
- TTL-based cleanup (locks expire automatically)

---

## Vendor Bot Flow

### Implementation

**File:** `src/ae/telegram_polling.py` → `handle_vendor_command()`

### Bot Initialization

**Process:**
1. Find Telegram channel with `bot_type == "vendor"` and `telegram_bot_token`
2. Create `TelegramPollingClient` instance
3. Start polling loop (same as customer bot)

### Commands

#### `/start` or `/help`

**Response:**
```
🤖 Vendor Bot Commands:

/bookings - List pending bookings
/confirm <booking_id> - Confirm a booking
/paid <payment_id> - Mark payment as paid
/complete <booking_id> - Mark booking as completed

Example:
  /bookings
  /confirm br_123
  /paid pi_456
  /complete br_123
```

#### `/bookings`

**Handler:** `handle_list_bookings()`

**Process:**
1. Fetch bookings with status:
   - `deposit_requested` (waiting for payment)
   - `confirmed` (ready to complete)

2. Build message:
   ```
   📋 Pending Bookings:
   
   • br_telegram_123_1234567890
     John Doe | Status: deposit_requested | Payment: requested (pi_123)
     Time: Morning (9am-12pm)
   
   • br_telegram_456_1234567891
     Jane Smith | Status: confirmed
     Time: Afternoon (12pm-5pm)
   ```

3. Limit to 10 bookings for readability

#### `/confirm <booking_id>`

**Handler:** `handle_confirm_booking()`

**Process:**
1. Fetch booking by `request_id`
2. Check if already confirmed
3. Update booking status:
   ```python
   updated = update_booking_status(db_path, booking_id, "confirmed")
   ```

4. **Customer Notification:**
   ```python
   await self._notify_customer_booking_confirmed(booking)
   ```
   - Gets `telegram_chat_id` from booking meta
   - Finds customer bot channel
   - Sends confirmation message:
     ```
     ✅ Great news! Your booking has been confirmed!
     
     📋 Booking ID: br_telegram_123_1234567890
     📦 Package: Thai Traditional Massage
     ⏰ Preferred time: Morning (9am-12pm)
     
     We're looking forward to serving you!
     ```

5. **Event Emission:**
   - Emits `op.booking.confirmed` event
   - Triggers chat automation (service reminders)

#### `/paid <payment_id>`

**Handler:** `handle_mark_paid()`

**Process:**
1. Fetch payment intent by `intent_id`
2. Check if already paid
3. Mark payment as paid:
   ```python
   updated = mark_payment_intent_paid(db_path, payment_id)
   ```

4. **Automatic Booking Confirmation:**
   - Payment status change triggers booking confirmation
   - Booking status updated to `confirmed`

5. **Response:**
   ```
   ✅ Payment 'pi_123' marked as paid!
   Amount: ฿500
   Booking automatically confirmed.
   ```

#### `/complete <booking_id>`

**Handler:** `handle_complete_booking()`

**Process:**
1. Fetch booking by `request_id`
2. Validate status (must be `confirmed`)
3. Update booking status:
   ```python
   updated = update_booking_status(db_path, booking_id, "completed")
   ```

4. **Event Emission:**
   - Emits `op.booking.completed` event
   - Triggers chat automation (review request)

5. **Response:**
   ```
   ✅ Booking 'br_telegram_123_1234567890' marked as completed!
   ```

---

## Moneyboard API

### Implementation File

**File:** `src/ae/console_routes_money_board.py`

### Endpoints

#### `GET /api/money-board`

**Purpose:** Get moneyboard data grouped by status columns.

**Query Parameters:**
- `db` - Database path (optional)
- `client_id` - Filter by client (optional)

**Process:**
1. Fetch all leads (optionally filtered by `client_id`)
2. Fetch all booking requests
3. Fetch all payment intents
4. Group leads by status:
   ```python
   def _get_status_for_lead(lead, booking_request, payment_intent) -> str:
       if not booking_request:
           return "new"
       
       status = booking_request.get("status", "")
       preferred_window = booking_request.get("preferred_window")
       
       if status == "requested":
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
   ```

5. **Status Columns:**
   - `new` - New leads (no package selected)
   - `package_selected` - Package selected, missing time window
   - `time_window_set` - Time window set, ready for deposit
   - `deposit_requested` - Deposit requested, waiting for payment
   - `confirmed` - Confirmed (deposit paid)
   - `complete` - Service completed
   - `closed` - Closed (done)

**Response:**
```json
{
  "columns": [
    {
      "status": "new",
      "count": 5,
      "items": [
        {
          "lead_id": 123,
          "lead_name": "John Doe",
          "lead_phone": "+1234567890",
          "lead_email": "john@example.com",
          "request_id": null,
          "package_id": null,
          "preferred_window": null,
          "amount": null,
          "status": "new"
        }
      ]
    },
    {
      "status": "package_selected",
      "count": 2,
      "items": [...]
    }
  ]
}
```

#### `POST /api/money-board/{lead_id}/send-package-menu`

**Purpose:** Send package menu template to lead.

**Process:**
1. Fetch active packages
2. Build package list:
   ```python
   package_list = "\n".join([
       f"{i+1}. {p.name} - ฿{p.price:.0f} ({p.duration_min} min)"
       for i, p in enumerate(packages)
   ])
   ```

3. Call `send_template()` with:
   - `template_key: "money_board.package_menu"`
   - `context: {"package_list": package_list}`

#### `POST /api/money-board/{request_id}/set-time-window`

**Purpose:** Set time window for booking request.

**Request Body:**
```json
{
  "preferred_window": "morning",
  "location": "123 Main St"  // optional
}
```

**Process:**
1. Update booking request:
   ```python
   updated = repo.update_booking_status(
       db_path,
       request_id,
       "deposit_requested",  # Move to deposit_requested
       preferred_window=payload.preferred_window,
       location=payload.location,
   )
   ```

#### `POST /api/money-board/{request_id}/request-deposit`

**Purpose:** Request deposit payment (creates payment intent).

**Request Body:**
```json
{
  "amount": 500.0,
  "method": "promptpay",
  "payment_link": "https://payment.link/..."  // optional
}
```

**Process:**
1. Create payment intent:
   ```python
   intent_id = f"pi_{request_id}_{int(now.timestamp())}"
   
   pi = PaymentIntent(
       intent_id=intent_id,
       lead_id=booking.lead_id,
       booking_request_id=request_id,
       amount=payload.amount,
       method=payload.method,
       status="requested",
       payment_link=payload.payment_link,
       meta_json={},
       created_at=now,
       updated_at=now,
   )
   created = repo.create_payment_intent(db_path, pi)
   ```

2. Send deposit request template:
   ```python
   send_template(
       SendTemplateRequest(
           lead_id=booking.lead_id,
           template_key="money_board.deposit_request",
           context={
               "package_name": "Service",
               "amount": payload.amount,
               "payment_link": payload.payment_link or "",
               "promptpay_number": "",
           },
       )
   )
   ```

#### `POST /api/money-board/{intent_id}/mark-paid`

**Purpose:** Mark payment intent as paid.

**Process:**
1. Update payment intent:
   ```python
   updated = repo.mark_payment_intent_paid(db_path, intent_id)
   ```

2. **Automatic Booking Confirmation:**
   - Payment status change triggers booking confirmation
   - Booking status updated to `confirmed`

#### `POST /api/money-board/{request_id}/mark-completed`

**Purpose:** Mark booking request as completed.

**Process:**
1. Update booking status:
   ```python
   updated = repo.update_booking_status(db_path, request_id, "completed")
   ```

2. **Event Emission:**
   - Emits `op.booking.completed` event
   - Triggers chat automation (review request)

#### `POST /api/money-board/{request_id}/close`

**Purpose:** Close booking request.

**Process:**
1. Update booking status:
   ```python
   updated = repo.update_booking_status(db_path, request_id, "closed")
   ```

#### `POST /api/money-board/send-template`

**Purpose:** Send a template message to a lead's chat channel.

**Request Body:**
```json
{
  "lead_id": 123,
  "template_key": "money_board.package_menu",
  "context": {
    "package_list": "1. Package A - ฿500\n2. Package B - ฿700"
  }
}
```

**Process:**
1. Get lead and client_id
2. Find chat channel for client:
   ```python
   channel = _find_channel_for_client(db_path, lead.client_id)
   ```

3. Get or create conversation:
   ```python
   conversation = get_or_create_chat_conversation(
       db_path,
       conversation_id=f"conv_lead_{lead_id}_{timestamp}",
       channel_id=channel.channel_id,
       external_thread_id=f"lead-{lead_id}",
       lead_id=str(lead_id),
   )
   ```

4. Render template:
   ```python
   message_text = render_template(db_path, payload.template_key, context)
   ```

5. **Telegram Delivery:**
   ```python
   try:
       from .telegram_delivery import send_message
       send_message(db_path, conversation.conversation_id, message_text)
   except Exception:
       # Best-effort: don't fail if Telegram delivery fails
       pass
   ```

6. Store message:
   ```python
   insert_chat_message(
       db_path,
       message_id=message_id,
       conversation_id=conversation.conversation_id,
       direction="outbound",
       text=message_text,
       ts=datetime.utcnow().isoformat() + "Z",
   )
   ```

---

## Backend Modules

### Core Modules

#### `src/ae/service.py`

**Functions:**
- `intake_lead()` - Creates lead from form submission
  - Spam detection
  - Database insert
  - Activity logging
  - Event emission

- `set_lead_outcome()` - Updates lead booking status
  - Updates `booking_status`, `booking_value`, `booking_currency`
  - Emits booking events (`op.booking.created`, `op.booking.confirmed`, etc.)

#### `src/ae/repo_leads.py`

**Functions:**
- `insert_lead()` - Insert lead into database
- `get_lead()` - Get lead by ID
- `list_leads()` - List leads with filters
- `get_or_create_lead_by_telegram_chat_id()` - Get or create lead from Telegram chat_id (indexed lookup)

#### `src/ae/repo_booking_requests.py`

**Functions:**
- `create_booking_request()` - Create new booking request
- `get_booking_request()` - Get booking by request_id
- `list_booking_requests()` - List bookings with filters
- `update_booking_status()` - Update booking status
- `get_recent_booking_request()` - Check for duplicate bookings
- `get_active_bookings_for_lead()` - Get active bookings for lead
- `cancel_booking_request()` - Cancel booking (status → "closed")

#### `src/ae/repo_payment_intents.py`

**Functions:**
- `create_payment_intent()` - Create payment intent
- `get_payment_intent()` - Get payment intent by ID
- `list_payment_intents()` - List payment intents
- `mark_payment_intent_paid()` - Mark payment as paid
  - Updates payment intent status
  - Creates Payment record
  - Automatically confirms booking

#### `src/ae/repo_chat_channels.py`

**Functions:**
- `upsert_chat_channel()` - Create or update chat channel
- `get_chat_channel()` - Get channel by ID
- `list_chat_channels()` - List channels with filters

#### `src/ae/repo_chat_conversations.py`

**Functions:**
- `get_or_create_conversation()` - Get or create conversation
- `get_conversation()` - Get conversation by ID
- `list_conversations()` - List conversations with filters
- `create_conversation_with_message()` - Atomically create conversation and message

#### `src/ae/repo_chat_messages.py`

**Functions:**
- `insert_message()` - Insert chat message
- `list_messages()` - List messages for conversation

#### `src/ae/repo_chat_automations.py`

**Functions:**
- `create_automation()` - Schedule automated message
- `list_due_automations()` - Get automations due to send
- `mark_sent()` - Mark automation as sent

#### `src/ae/repo_service_packages.py`

**Functions:**
- `get_package()` - Get package by ID
- `list_packages()` - List packages with filters

#### `src/ae/telegram_delivery.py`

**Functions:**
- `send_message()` - Send message via Telegram Bot API
  - Gets conversation and channel
  - Extracts bot token from channel meta
  - Extracts chat_id from conversation external_thread_id
  - Calls `_send_telegram()` from `repo_alerts.py`

#### `src/ae/chat_templates.py`

**Functions:**
- `render_template()` - Render template with context
  - Fetches template from database or uses default
  - Substitutes `{variable}` placeholders
  - Returns rendered text

**Default Templates:**
- `money_board.package_menu` - Package selection menu
- `money_board.time_window_request` - Time window selection
- `money_board.deposit_request` - Deposit payment request
- `money_board.deposit_reminder` - Deposit reminder
- `money_board.service_reminder_24h` - 24-hour service reminder
- `money_board.service_reminder_2h` - 2-hour service reminder
- `money_board.review_request` - Review request after completion

---

## Event System

### Event Bus

**File:** `src/ae/event_bus.py`

**Purpose:** Emit and handle operational events.

**Key Events:**

#### `op.lead.created`
Emitted when lead is created.

**Payload:**
```json
{
  "lead_id": 123,
  "client_id": "demo1",
  "source": "landing_page"
}
```

#### `op.chat.message_received`
Emitted when chat message is received.

**Payload:**
```json
{
  "conversation_id": "conv_telegram_123",
  "text": "morning",
  "channel": "telegram",
  "chat_id": "123"
}
```

#### `op.chat.message_sent`
Emitted when chat message is sent.

**Payload:**
```json
{
  "conversation_id": "conv_telegram_123",
  "text": "✅ Package Selected!",
  "template_key": "money_board.package_menu"
}
```

#### `op.booking.created`
Emitted when booking is created.

**Payload:**
```json
{
  "booking_id": "lead-123",
  "lead_id": 123,
  "booking_status": "booked",
  "booking_value": 500.0,
  "booking_currency": "THB"
}
```

#### `op.booking.confirmed`
Emitted when booking is confirmed.

**Payload:**
```json
{
  "booking_id": "lead-123",
  "lead_id": 123,
  "request_id": "br_telegram_123_1234567890",
  "booking_status": "confirmed"
}
```

**Triggers:**
- Chat automation: Service reminders (24h, 2h)

#### `op.booking.completed`
Emitted when booking is completed.

**Payload:**
```json
{
  "booking_id": "lead-123",
  "lead_id": 123,
  "request_id": "br_telegram_123_1234567890",
  "booking_status": "completed"
}
```

**Triggers:**
- Chat automation: Review request

#### `op.payment.captured`
Emitted when payment is captured.

**Payload:**
```json
{
  "lead_id": 123,
  "amount": 500.0,
  "currency": "THB",
  "payment_link": "https://..."
}
```

**Triggers:**
- Chat automation: 24-hour follow-up

---

## Chat Automation

### Implementation

**File:** `src/ae/chat_automation.py`

### Hooks

#### `_on_booking_request_confirmed()`

**Trigger:** `op.booking.confirmed` event

**Process:**
1. Find conversation for lead
2. Calculate service date (from booking `created_at` + 1 day placeholder)
3. Schedule 24-hour reminder:
   ```python
   reminder_24h_at = service_date - timedelta(hours=24)
   create_automation(
       db_path,
       conversation_id=conv_id,
       template_key="money_board.service_reminder_24h",
       due_at=reminder_24h_at,
       context_json={
           "package_name": package_name,
           "time_window": time_window,
           "lead_id": lead_id,
       }
   )
   ```

4. Schedule 2-hour reminder:
   ```python
   reminder_2h_at = service_date - timedelta(hours=2)
   create_automation(
       db_path,
       conversation_id=conv_id,
       template_key="money_board.service_reminder_2h",
       due_at=reminder_2h_at,
       context_json={
           "package_name": package_name,
           "time_window": time_window,
           "location": location,
           "lead_id": lead_id,
       }
   )
   ```

#### `_on_booking_request_completed()`

**Trigger:** `op.booking.completed` event

**Process:**
1. Find conversation for lead
2. Schedule review request (1 hour after completion):
   ```python
   create_automation(
       db_path,
       conversation_id=conv_id,
       template_key="money_board.review_request",
       due_at=datetime.utcnow() + timedelta(hours=1),
       context_json={
           "package_name": package_name,
           "lead_id": lead_id,
       }
   )
   ```

#### `_on_message_received()`

**Trigger:** `op.chat.message_received` event

**Process:**
1. Check if message contains "price" or "pay"
2. Schedule payment request template:
   ```python
   create_automation(
       db_path,
       conversation_id=conv_id,
       template_key="payment_request",
       due_at=datetime.utcnow(),
       context_json={
           "payment_link": "TBD",
           "amount": "?",
           "currency": "?",
       }
   )
   ```

### Automation Runner

**Function:** `run_due_chat_automations()`

**Process:**
1. Fetch due automations:
   ```python
   due = list_due_automations(db_path, now=now, limit=limit)
   ```

2. For each automation:
   - Render template:
     ```python
     body = render_template(db_path, a.template_key, a.context_json)
     ```
   
   - **Telegram Delivery:**
     ```python
     try:
         from .telegram_delivery import send_message
         send_message(db_path, a.conversation_id, body)
     except Exception:
         # Best-effort: don't fail if Telegram delivery fails
         pass
     ```
   
   - Store message:
     ```python
     insert_message(
         db_path,
         conversation_id=a.conversation_id,
         direction="outbound",
         text=body,
         payload_json={"template_key": a.template_key}
     )
     ```
   
   - Emit event:
     ```python
     EventBus.emit_topic(
         db_path,
         topic="op.chat.message_sent",
         aggregate_type="chat",
         aggregate_id=a.conversation_id,
         payload={
             "conversation_id": a.conversation_id,
             "text": body,
             "template_key": a.template_key,
         }
     )
     ```
   
   - Mark as sent:
     ```python
     mark_sent(db_path, a.automation_id, now)
     ```

**Execution:**
- Called periodically (e.g., every minute)
- Processes up to 50 automations per run
- Best-effort delivery (doesn't fail if Telegram unavailable)

---

## Complete Flow Diagrams

### End-to-End Booking Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Landing Page                                                 │
│    - User fills form                                            │
│    - Clicks "Get Quote" / Package                               │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Lead Creation                                                │
│    POST /lead                                                    │
│    - Creates lead_intake record                                  │
│    - Status: "new"                                               │
│    - Stores UTM, referrer, etc.                                 │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Telegram Deep Link                                           │
│    t.me/bot?start=package_pkg123                                │
│    - Redirects to Telegram bot                                  │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Customer Bot - /start                                        │
│    - Cancels existing bookings                                  │
│    - Shows package confirmation                                 │
│    - Stores pending_package_id                                  │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Customer Confirms Package                                     │
│    User: "yes"                                                   │
│    - Shows timeslot options                                     │
│    - Sets booking_state: "awaiting_time_window"                │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. Customer Selects Time Window                                  │
│    User: "morning" or "1"                                        │
│    - Creates booking_request                                    │
│    - Status: "requested"                                        │
│    - preferred_window: "Morning (9am-12pm)"                    │
│    - Notifies vendor bot                                        │
└────────────────────┬────────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌──────────────────┐    ┌──────────────────┐
│ Customer         │    │ Vendor Bot       │
│ Confirmation     │    │ Notification     │
│                  │    │                  │
│ ✅ Booking       │    │ 🔔 New Booking   │
│ created!         │    │ Request          │
└──────────────────┘    └──────────────────┘
         │                       │
         │                       ▼
         │              ┌──────────────────┐
         │              │ Vendor: /bookings│
         │              │ - Lists pending  │
         │              │   bookings       │
         │              └──────────────────┘
         │                       │
         │                       ▼
         │              ┌──────────────────┐
         │              │ Operator:        │
         │              │ Request Deposit  │
         │              │ (via Moneyboard) │
         │              └──────────────────┘
         │                       │
         │                       ▼
         │              ┌──────────────────┐
         │              │ Payment Intent   │
         │              │ Created          │
         │              │ - Status:        │
         │              │   "requested"    │
         │              │ - Customer       │
         │              │   notified       │
         │              └──────────────────┘
         │                       │
         │                       ▼
         │              ┌──────────────────┐
         │              │ Customer Pays    │
         │              │ (external)       │
         │              └──────────────────┘
         │                       │
         │                       ▼
         │              ┌──────────────────┐
         │              │ Vendor: /paid    │
         │              │ pi_123            │
         │              │ - Payment marked │
         │              │   paid           │
         │              │ - Booking auto-  │
         │              │   confirmed      │
         │              └──────────────────┘
         │                       │
         │                       ▼
         │              ┌──────────────────┐
         │              │ Booking          │
         │              │ Confirmed        │
         │              │ - Status:        │
         │              │   "confirmed"   │
         │              │ - Customer       │
         │              │   notified      │
         │              │ - Reminders      │
         │              │   scheduled     │
         │              └──────────────────┘
         │                       │
         │                       ▼
         │              ┌──────────────────┐
         │              │ Service Day      │
         │              │ - 24h reminder   │
         │              │   sent           │
         │              │ - 2h reminder   │
         │              │   sent           │
         │              └──────────────────┘
         │                       │
         │                       ▼
         │              ┌──────────────────┐
         │              │ Service          │
         │              │ Delivered        │
         │              └──────────────────┘
         │                       │
         │                       ▼
         │              ┌──────────────────┐
         │              │ Vendor: /complete│
         │              │ br_123           │
         │              │ - Booking       │
         │              │   completed     │
         │              │ - Review        │
         │              │   requested     │
         │              └──────────────────┘
         │                       │
         └───────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. Booking Completed                                            │
│    - Status: "completed"                                        │
│    - Review request scheduled                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Moneyboard Status Flow

```
new
  │
  ├─> [Package Selected] ──> package_selected
  │                              │
  │                              ├─> [Time Window Set] ──> time_window_set
  │                              │                              │
  │                              │                              ├─> [Deposit Requested] ──> deposit_requested
  │                              │                              │                              │
  │                              │                              │                              ├─> [Payment Paid] ──> confirmed
  │                              │                              │                              │                              │
  │                              │                              │                              │                              ├─> [Service Completed] ──> complete
  │                              │                              │                              │                              │                              │
  │                              │                              │                              │                              │                              └─> closed
```

### Database Relationships

```
clients
  │
  ├─> lead_intake (client_id)
  │      │
  │      ├─> booking_requests (lead_id)
  │      │      │
  │      │      ├─> payment_intents (booking_request_id)
  │      │      │
  │      │      └─> chat_conversations (via lead_id)
  │      │
  │      └─> chat_conversations (lead_id)
  │
  ├─> service_packages (client_id)
  │      │
  │      └─> booking_requests (package_id)
  │
  └─> chat_channels (meta_json.client_id)
         │
         └─> chat_conversations (channel_id)
                │
                └─> chat_messages (conversation_id)
                       │
                       └─> chat_automations (conversation_id)
```

---

## Key Implementation Details

### Telegram Bot Token Storage

- Stored in `chat_channels.meta_json.telegram_bot_token`
- Per-channel configuration (supports multiple bots)
- Vendor bot identified by `bot_type: "vendor"` in meta

### Conversation Mapping

- Telegram `chat_id` stored in `chat_conversations.external_thread_id`
- Conversation ID format: `conv_telegram_{chat_id}`
- Links to lead via `lead_id` field

### Booking Request ID Generation

- Format: `br_telegram_{chat_id}_{timestamp_ms}`
- Ensures uniqueness across concurrent bookings
- Timestamp in milliseconds for precision

### Payment Intent ID Generation

- Format: `pi_{request_id}_{timestamp}`
- Links to booking request
- Timestamp ensures uniqueness

### State Management

- **Redis-backed** (if `AE_REDIS_URL` set):
  - Distributed locks
  - Message deduplication
  - Cooldown tracking
- **In-memory fallback** (single instance):
  - Thread-safe locks
  - In-memory sets/dicts
  - TTL-based cleanup

### Error Handling

- **Best-effort delivery:** Telegram failures don't break flow
- **Graceful degradation:** Falls back to message storage if delivery fails
- **Duplicate prevention:** Multiple layers (locks, cooldowns, deduplication)

### Performance Optimizations

- **Caching:** Package lookups cached (5-minute TTL)
- **Indexed lookups:** Telegram chat_id indexed for fast lead retrieval
- **Batch operations:** Multiple bookings fetched in single query
- **Lazy loading:** Channel info fetched on-demand

---

## Security Considerations

### Rate Limiting

- Public endpoints rate-limited (`rate_limit_or_429()`)
- Telegram webhook rate-limited
- Cooldown mechanisms prevent abuse

### Spam Detection

- Honeypot fields
- Spam score calculation
- IP hint tracking (last octet removed)

### Input Validation

- Field length limits (name: 80, phone: 32, email: 254, message: 2000)
- SQL injection prevention (parameterized queries)
- XSS prevention (template rendering)

### Authentication

- Moneyboard API requires operator role (`require_role("operator")`)
- Public endpoints unauthenticated (rate-limited)

---

## Testing

### Unit Tests

- `tests/test_money_board_chat_integration.py` - Integration tests
- `tests/test_chat_automation_v1.py` - Automation tests
- `tests/test_lead_intake.py` - Lead intake tests

### Manual Testing Flow

1. **Landing Page:**
   - Submit form → Verify lead created
   - Click package → Verify Telegram redirect

2. **Customer Bot:**
   - Send `/start package_pkg123` → Verify package confirmation
   - Reply "yes" → Verify timeslot selection
   - Select timeslot → Verify booking created

3. **Vendor Bot:**
   - Send `/bookings` → Verify bookings listed
   - Send `/paid pi_123` → Verify payment marked paid
   - Send `/complete br_123` → Verify booking completed

4. **Moneyboard:**
   - Open `/money-board` → Verify columns populated
   - Perform actions → Verify status updates

---

## Conclusion

This document provides a comprehensive audit of the Moneyboard implementation, covering:

- **Complete flow** from landing page to booking completion
- **Database schema** with all tables and relationships
- **API endpoints** with request/response details
- **Bot implementations** (customer and vendor)
- **Event system** and automation triggers
- **State management** and error handling

The system is designed for:
- **Scalability:** Redis-backed distributed state
- **Reliability:** Best-effort delivery with graceful degradation
- **Maintainability:** Clear separation of concerns
- **Extensibility:** Event-driven architecture

For questions or clarifications, refer to the source code files listed in each section.
