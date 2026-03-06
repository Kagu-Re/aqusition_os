# Moneyboard Implementation Details - Technical Supplement

**Version:** 1.0  
**Date:** February 7, 2026  
**Purpose:** Detailed technical specifications for audit and implementation reference

---

## Table of Contents

1. [Status Enum Lists](#status-enum-lists)
2. [Booking/Payment Transition Rules](#bookingpayment-transition-rules)
3. [Vendor Bot Authentication](#vendor-bot-authentication)
4. [Database Schema Snippets](#database-schema-snippets)
5. [Timezone Policy](#timezone-policy)
6. [Retry Policy](#retry-policy)
7. [Traffic Expectations & SQLite Sizing](#traffic-expectations--sqlite-sizing)

---

## Status Enum Lists

### Lead Status (`lead_intake.status`)

**Database Values:**
- `"new"` - Newly created lead (default)
- `"spam"` - Detected as spam (spam_score >= 60)
- `"contacted"` - Operator has contacted the lead
- `"qualified"` - Lead qualified for booking
- `"converted"` - Lead converted to booking
- `"lost"` - Lead lost/not converted

**API Usage:**
- Created via `POST /lead` → `"new"` (or `"spam"` if detected)
- Updated via `POST /api/leads/{lead_id}/outcome` → any status

**Code Reference:**
- `src/ae/service.py` - `intake_lead()` sets `status="new"` or `status="spam"`
- `src/ae/models.py` - `LeadIntake.status: str = "new"`

### Lead Booking Status (`lead_intake.booking_status`)

**Database Values:**
- `"none"` - No booking (default)
- `"booked"` - Booking created
- `"confirmed"` - Booking confirmed
- `"completed"` - Service completed
- `"cancelled"` / `"canceled"` - Booking cancelled

**API Usage:**
- Updated via `POST /api/leads/{lead_id}/outcome` with `booking_status` parameter
- Automatically updated when booking status changes

**Code Reference:**
- `src/ae/service.py` - `set_lead_outcome()` updates `booking_status`
- `src/ae/models.py` - `LeadIntake.booking_status: str = "none"`

### Booking Request Status (`booking_requests.status`)

**Database Values:**
- `"requested"` - Initial booking request (default)
- `"deposit_requested"` - Deposit payment requested
- `"confirmed"` - Booking confirmed (deposit paid or manually confirmed)
- `"completed"` - Service completed
- `"closed"` - Booking closed (final state)
- `"cancelled"` / `"canceled"` - Booking cancelled

**API Usage:**
- Created via `POST /api/booking-requests` → `"requested"`
- Updated via `POST /api/money-board/{request_id}/set-time-window` → `"deposit_requested"`
- Updated via `POST /api/money-board/{request_id}/mark-completed` → `"completed"`
- Updated via `POST /api/money-board/{request_id}/close` → `"closed"`
- Updated via vendor bot `/confirm` → `"confirmed"`

**Code Reference:**
- `src/ae/models.py` - `BookingRequest.status: str = "requested"`
- `src/ae/repo_booking_requests.py` - `update_booking_status()` validates transitions
- `src/ae/console_routes_money_board.py` - `_get_status_for_lead()` maps to moneyboard columns

**Moneyboard Column Mapping:**
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

**Moneyboard Columns:**
- `"new"` - New leads (no booking request)
- `"package_selected"` - Package selected, missing time window
- `"time_window_set"` - Time window set, ready for deposit
- `"deposit_requested"` - Deposit requested, waiting for payment
- `"confirmed"` - Confirmed (deposit paid)
- `"complete"` - Service completed
- `"closed"` - Closed (done)

### Payment Intent Status (`payment_intents.status`)

**Database Values:**
- `"requested"` - Payment intent created (default)
- `"paid"` - Payment marked as paid

**API Usage:**
- Created via `POST /api/money-board/{request_id}/request-deposit` → `"requested"`
- Updated via `POST /api/money-board/{intent_id}/mark-paid` → `"paid"`
- Updated via vendor bot `/paid <intent_id>` → `"paid"`

**Code Reference:**
- `src/ae/models.py` - `PaymentIntent.status: str = "requested"`
- `src/ae/repo_payment_intents.py` - `mark_payment_intent_paid()` updates to `"paid"`

### Payment Status (`payments.status`)

**Database Values (from `PaymentStatus` enum):**
- `"pending"` - Created but not confirmed
- `"authorized"` - Authorized but not captured
- `"captured"` - Paid
- `"failed"` - Payment failed
- `"cancelled"` - Payment cancelled
- `"refunded"` - Payment refunded

**Code Reference:**
- `src/ae/enums.py` - `PaymentStatus` enum
- `src/ae/models.py` - `Payment.status: PaymentStatus = PaymentStatus.pending`

### Chat Automation Status (`chat_automations.status`)

**Database Values:**
- `"pending"` - Scheduled, not yet sent (default)
- `"sent"` - Successfully sent
- `"cancelled"` - Cancelled before sending

**Code Reference:**
- `src/ae/models.py` - `ChatAutomation.status: str = "pending"`
- `src/ae/repo_chat_automations.py` - `mark_sent()` updates to `"sent"`

### Chat Conversation Status (`chat_conversations.status`)

**Database Values:**
- `"open"` - Conversation is active (default)
- `"closed"` - Conversation closed
- `"archived"` - Conversation archived

**Code Reference:**
- `src/ae/models.py` - `ChatConversation.status: str = "open"`

---

## Booking/Payment Transition Rules

### Transition Registry

**File:** `src/ae/transition_registry.py`

**Purpose:** Enforces state machine transitions for booking requests and payment intents.

### Booking Request Transitions

**Allowed Transitions:**
```python
"booking_request": {
    "op.booking.requested": TransitionRule(
        topic="op.booking.requested",
        from_state=NONE_STATE,  # "__none__"
        to_state="requested"
    ),
    "op.booking.deposit_requested": TransitionRule(
        topic="op.booking.deposit_requested",
        from_state="requested",
        to_state="deposit_requested"
    ),
    "op.booking.confirmed": TransitionRule(
        topic="op.booking.confirmed",
        from_state="deposit_requested",  # MUST be deposit_requested
        to_state="confirmed"
    ),
    "op.booking.completed": TransitionRule(
        topic="op.booking.completed",
        from_state="confirmed",  # MUST be confirmed
        to_state="completed"
    ),
    "op.booking.closed": TransitionRule(
        topic="op.booking.closed",
        from_state="completed",  # MUST be completed
        to_state="closed"
    ),
}
```

**Transition Enforcement:**

**File:** `src/ae/repo_booking_requests.py` - `update_booking_status()`

```python
# Status transition validation
if status == "deposit_requested" and old_status == "requested":
    event_topic = "op.booking.deposit_requested"
elif status == "confirmed" and old_status == "deposit_requested":
    event_topic = "op.booking.confirmed"
elif status == "completed" and old_status == "confirmed":
    event_topic = "op.booking.completed"
elif status == "closed" and old_status == "completed":
    event_topic = "op.booking.closed"
elif status in ("cancelled", "canceled") and old_status not in ("cancelled", "canceled", "closed", "completed"):
    event_topic = "op.booking.cancelled"
```

**Prerequisites for `/confirm` (Vendor Bot):**

1. **Booking must exist:**
   ```python
   booking = get_booking_request(db_path, booking_id)
   if not booking:
       return  # Error: booking not found
   ```

2. **Booking must NOT already be confirmed:**
   ```python
   if booking.status == "confirmed":
       return  # Already confirmed
   ```

3. **Booking status should be `deposit_requested` (enforced by transition rule):**
   - Transition rule requires: `from_state="deposit_requested"` → `to_state="confirmed"`
   - However, code allows direct update without strict enforcement
   - **Note:** Transition engine validates events, but direct DB updates bypass this

4. **After confirmation:**
   - Lead `booking_status` updated to `"confirmed"`
   - Event `op.booking.confirmed` emitted
   - Chat automation triggers (service reminders scheduled)

**Prerequisites for `/paid` (Vendor Bot):**

1. **Payment intent must exist:**
   ```python
   payment_intent = get_payment_intent(db_path, payment_id)
   if not payment_intent:
       return  # Error: payment intent not found
   ```

2. **Payment intent must NOT already be paid:**
   ```python
   if payment_intent.status == "paid":
       return  # Already paid
   ```

3. **Automatic booking confirmation:**
   ```python
   # After marking payment as paid:
   # 1. Payment intent status → "paid"
   # 2. Payment record created
   # 3. Booking request status → "confirmed" (automatic)
   # 4. Lead booking_status → "confirmed"
   ```

**File:** `src/ae/repo_payment_intents.py` - `mark_payment_intent_paid()`

```python
def mark_payment_intent_paid(db_path: str, intent_id: str) -> Optional[PaymentIntent]:
    # 1. Update payment intent status
    con.execute(
        "UPDATE payment_intents SET status=?, updated_at=? WHERE intent_id=?",
        ("paid", updated_at, intent_id),
    )
    
    # 2. Create Payment record
    payment = repo.create_payment(...)
    
    # 3. Update booking request to confirmed
    booking = repo.get_booking_request(db_path, existing["booking_request_id"])
    if booking and booking.status == "deposit_requested":
        repo.update_booking_status(
            db_path,
            existing["booking_request_id"],
            "confirmed"
        )
    
    # 4. Emit event
    EventBus.emit_topic(
        db_path,
        topic="op.payment_intent.paid",
        ...
    )
```

### Payment Intent Transitions

**Allowed Transitions:**
```python
"payment_intent": {
    "op.payment_intent.requested": TransitionRule(
        topic="op.payment_intent.requested",
        from_state=NONE_STATE,
        to_state="requested"
    ),
    "op.payment_intent.paid": TransitionRule(
        topic="op.payment_intent.paid",
        from_state="requested",  # MUST be requested
        to_state="paid"
    ),
}
```

### Payment Transitions (Full Payment Lifecycle)

**Allowed Transitions:**
```python
"payment": {
    "op.payment.created": TransitionRule(
        topic="op.payment.created",
        from_state=NONE_STATE,
        to_state="pending"
    ),
    "op.payment.authorized": TransitionRule(
        topic="op.payment.authorized",
        from_state="pending",
        to_state="authorized"
    ),
    "op.payment.captured": TransitionRule(
        topic="op.payment.captured",
        from_state="authorized",
        to_state="captured"
    ),
    "op.payment.captured_direct": TransitionRule(
        topic="op.payment.captured_direct",
        from_state="pending",
        to_state="captured"
    ),
    "op.payment.failed": TransitionRule(
        topic="op.payment.failed",
        from_state="pending",
        to_state="failed"
    ),
    "op.payment.refunded": TransitionRule(
        topic="op.payment.refunded",
        from_state="captured",
        to_state="refunded"
    ),
}
```

**Payment Binding Rules:**

**File:** `src/ae/repo_payments.py` - `update_payment_status()`

```python
# Cannot update payment for cancelled booking
bs = (getattr(lead, "booking_status", None) or "").strip().lower()
if bs in ("cancelled", "canceled"):
    raise PaymentBindingError("Cannot update payment for a cancelled booking")

# Cannot capture payment unless booking is confirmed or completed
if status == PaymentStatus.captured and bs not in ("confirmed", "completed"):
    raise PaymentBindingError("Cannot capture payment unless booking is confirmed or completed")
```

---

## Vendor Bot Authentication

### Current Implementation

**File:** `src/ae/telegram_polling.py` - `handle_vendor_command()`

**Authentication Model:**
- **No explicit authentication** - Any Telegram user can send commands to vendor bot
- **Identification:** Bot identifies vendor bot by `bot_type == "vendor"` in channel meta
- **Authorization:** None - all commands are accessible to anyone who knows the bot

### Vendor Chat ID Configuration

**Storage:**
- Vendor chat ID stored in `chat_channels.meta_json.vendor_chat_id`
- Used to send booking notifications to vendor

**Configuration Script:**
- `set_vendor_chat_id.py` - Sets vendor chat ID for vendor bot channel

**Process:**
1. Vendor sends `/start` to vendor bot
2. Bot receives Telegram `chat_id` from message
3. Operator runs: `python set_vendor_chat_id.py --chat-id <chat_id>`
4. Bot stores `vendor_chat_id` in channel meta
5. Booking notifications sent to this chat_id

**Code Reference:**
```python
# Vendor bot identifies itself
is_vendor_bot = channel.meta_json.get("bot_type") == "vendor"

# Vendor chat ID lookup
vendor_chat_id = vendor_channel.meta_json.get("vendor_chat_id")

# Send notification
if vendor_chat_id:
    await vendor_client.send_message(str(vendor_chat_id), message)
```

### Admin Override

**Console API Authentication:**
- **File:** `src/ae/console_support.py` - `require_role()`
- **Roles:** `"admin"`, `"operator"`, `"viewer"`
- **Secret Bypass:** `X-AE-SECRET` header bypasses role checks

```python
def require_role(required_role: str):
    def _check(request: Request) -> AuthUser:
        # Admin bypass (legacy)
        secret = _get_secret()
        if secret:
            got = request.headers.get("X-AE-SECRET", "").strip()
            if got and got == secret:
                u = AuthUser(user_id="u_secret", username="secret_admin", role="admin")
                return u
        
        # Session-based auth
        u = require_auth(request)
        if u.role == "admin":
            return u  # Admin can do anything
        if required_role == "viewer" and u.role in ("viewer", "operator", "admin"):
            return u
        if required_role == "operator" and u.role in ("operator", "admin"):
            return u
        raise HTTPException(status_code=403, detail="insufficient_permissions")
    return _check
```

**Vendor Bot Commands:**
- **No authentication** - Commands are public
- **No allowlist** - Any Telegram user can use commands
- **No role checks** - All commands accessible

### Recommended Security Model (Not Implemented)

**Proposed Implementation:**

1. **Chat ID Allowlist:**
   ```python
   # Store allowed vendor chat IDs in channel meta
   allowed_chat_ids = channel.meta_json.get("allowed_vendor_chat_ids", [])
   
   if chat_id not in allowed_chat_ids:
       await self.send_message(chat_id, "❌ Unauthorized. Contact admin.")
       return
   ```

2. **Admin Commands:**
   ```python
   # Separate admin commands requiring secret
   if text.startswith("/admin_"):
       # Require secret verification
       if not verify_admin_secret(text):
           return
   ```

3. **Role-Based Commands:**
   ```python
   # Map chat IDs to roles
   vendor_roles = channel.meta_json.get("vendor_roles", {})
   user_role = vendor_roles.get(chat_id, "viewer")
   
   if command == "/confirm" and user_role not in ("operator", "admin"):
       return  # Insufficient permissions
   ```

**Current Risk:**
- **High:** Any Telegram user can manage bookings via vendor bot
- **Mitigation:** Keep vendor bot handle private, or implement allowlist

---

## Database Schema Snippets

### `booking_requests` Table

```sql
CREATE TABLE IF NOT EXISTS booking_requests (
    request_id TEXT PRIMARY KEY,
    lead_id INTEGER NOT NULL,
    package_id TEXT NOT NULL,
    preferred_window TEXT,  -- "morning" | "afternoon" | "evening" | "Morning (9am-12pm)" | etc.
    location TEXT,
    status TEXT NOT NULL,  -- "requested" | "deposit_requested" | "confirmed" | "completed" | "closed" | "cancelled"
    meta_json TEXT NOT NULL DEFAULT '{}',  -- JSON: {"telegram_chat_id": "...", "telegram_username": "...", "source": "telegram_bot"}
    created_at TEXT NOT NULL,  -- ISO-8601 UTC timestamp
    updated_at TEXT NOT NULL,  -- ISO-8601 UTC timestamp
    FOREIGN KEY(lead_id) REFERENCES lead_intake(lead_id),
    FOREIGN KEY(package_id) REFERENCES service_packages(package_id)
);

CREATE INDEX IF NOT EXISTS idx_booking_requests_lead ON booking_requests(lead_id);
CREATE INDEX IF NOT EXISTS idx_booking_requests_status ON booking_requests(status, updated_at);
CREATE INDEX IF NOT EXISTS idx_booking_requests_package ON booking_requests(package_id);
```

**Key Fields:**
- `request_id` - Format: `br_telegram_{chat_id}_{timestamp_ms}`
- `status` - See [Booking Request Status](#booking-request-status-booking_requestsstatus)
- `preferred_window` - Normalized format: `"Morning (9am-12pm)"`, `"Afternoon (12pm-5pm)"`, `"Evening (5pm-9pm)"`
- `meta_json` - Stores Telegram context, source, etc.

### `lead_intake` Table

```sql
CREATE TABLE IF NOT EXISTS lead_intake (
    lead_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,  -- ISO-8601 UTC timestamp
    source TEXT,  -- "landing_page" | "telegram_bot" | etc.
    page_id TEXT,
    client_id TEXT,
    name TEXT,  -- Max 80 chars
    phone TEXT,  -- Max 32 chars
    email TEXT,  -- Max 254 chars
    message TEXT,  -- Max 2000 chars
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    utm_term TEXT,
    utm_content TEXT,
    referrer TEXT,  -- Max 512 chars
    user_agent TEXT,  -- Max 512 chars
    ip_hint TEXT,  -- Coarse IP (last octet removed)
    spam_score INTEGER DEFAULT 0,  -- 0-100
    is_spam INTEGER DEFAULT 0,  -- 0 or 1
    status TEXT DEFAULT 'new',  -- "new" | "spam" | "contacted" | etc.
    booking_status TEXT DEFAULT 'none',  -- "none" | "booked" | "confirmed" | "completed" | "cancelled"
    booking_value REAL,
    booking_currency TEXT,
    booking_ts TEXT,
    meta_json TEXT NOT NULL DEFAULT '{}'  -- JSON: {"telegram_chat_id": "...", "telegram_username": "...", "spam_reasons": [...]}
);

CREATE INDEX IF NOT EXISTS idx_lead_intake_client ON lead_intake(client_id);
CREATE INDEX IF NOT EXISTS idx_lead_intake_status ON lead_intake(status);
CREATE INDEX IF NOT EXISTS idx_lead_intake_booking_status ON lead_intake(booking_status);
-- Note: Index on telegram_chat_id may exist for fast lookups
```

**Key Fields:**
- `lead_id` - Auto-increment primary key
- `status` - See [Lead Status](#lead-status-lead_intakestatus)
- `booking_status` - See [Lead Booking Status](#lead-booking-status-lead_intakebooking_status)
- `meta_json` - Stores Telegram context, spam reasons, UTM keys

### `chat_conversations` Table

```sql
CREATE TABLE IF NOT EXISTS chat_conversations (
    conversation_id TEXT PRIMARY KEY,  -- Format: "conv_telegram_{chat_id}"
    channel_id TEXT NOT NULL,
    external_thread_id TEXT,  -- Telegram chat_id (as string)
    lead_id TEXT,  -- Links to lead_intake.lead_id
    booking_id TEXT,  -- Links to booking aggregate (e.g., "lead-123")
    status TEXT NOT NULL DEFAULT 'open',  -- "open" | "closed" | "archived"
    meta_json TEXT NOT NULL DEFAULT '{}',  -- JSON: {"telegram_chat_id": "...", "telegram_username": "...", "pending_package_id": "...", "booking_state": "...", "timeslot_list": [...], "package_list": [...]}
    created_at TEXT NOT NULL,  -- ISO-8601 UTC timestamp
    updated_at TEXT NOT NULL  -- ISO-8601 UTC timestamp
);

CREATE INDEX IF NOT EXISTS idx_chat_conversations_channel_thread ON chat_conversations(channel_id, external_thread_id);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_lead ON chat_conversations(lead_id, created_at);
```

**Key Fields:**
- `conversation_id` - Format: `conv_telegram_{chat_id}`
- `external_thread_id` - Telegram `chat_id` (stored as string)
- `meta_json` - Stores:
  - `telegram_chat_id` - Telegram chat ID
  - `telegram_username` - Telegram username
  - `pending_package_id` - Package being selected
  - `booking_state` - Current state: `"awaiting_time_window"`
  - `timeslot_list` - Available timeslots with availability
  - `package_list` - Available packages for selection

### `chat_automations` Table

```sql
CREATE TABLE IF NOT EXISTS chat_automations (
    automation_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    template_key TEXT NOT NULL,  -- "money_board.service_reminder_24h" | "money_board.review_request" | etc.
    due_at TEXT NOT NULL,  -- ISO-8601 UTC timestamp
    status TEXT NOT NULL DEFAULT 'pending',  -- "pending" | "sent" | "cancelled"
    context_json TEXT NOT NULL DEFAULT '{}',  -- JSON: Template variables {"package_name": "...", "time_window": "...", "lead_id": "..."}
    created_at TEXT NOT NULL,  -- ISO-8601 UTC timestamp
    sent_at TEXT  -- ISO-8601 UTC timestamp (null until sent)
);

CREATE INDEX IF NOT EXISTS idx_chat_automations_due ON chat_automations(status, due_at);
```

**Key Fields:**
- `automation_id` - Unique automation ID
- `template_key` - Template to render (see `chat_templates.py`)
- `due_at` - When to send (UTC timestamp)
- `status` - See [Chat Automation Status](#chat-automation-status-chat_automationsstatus)
- `context_json` - Template context variables

**Template Keys:**
- `money_board.package_menu` - Package selection menu
- `money_board.time_window_request` - Time window selection
- `money_board.deposit_request` - Deposit payment request
- `money_board.deposit_reminder` - Deposit reminder
- `money_board.service_reminder_24h` - 24-hour service reminder
- `money_board.service_reminder_2h` - 2-hour service reminder
- `money_board.review_request` - Review request after completion

---

## Timezone Policy

### Current Implementation

**Policy:** **Single timezone (UTC)** - All timestamps stored and processed in UTC

**Storage Format:**
- All timestamps stored as ISO-8601 UTC strings: `"2026-02-07T12:34:56Z"`
- Database columns: `TEXT` type (not `DATETIME`)
- Format: `YYYY-MM-DDTHH:MM:SSZ` or `YYYY-MM-DDTHH:MM:SS+00:00`

**Code References:**

**File:** `src/ae/timeutils.py`
```python
def parse_utc(s: str) -> datetime:
    """Parse ISO-8601 UTC string (supports trailing 'Z')."""
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat() + "Z"
```

**File:** `src/ae/metrics.py`
```python
def parse_iso_z(s: str) -> Optional[datetime]:
    """Parse ISO-8601 UTC string."""
    if s.endswith("Z"):
        s = s[:-1]
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def now_utc() -> datetime:
    return datetime.now(timezone.utc)
```

**Common Pattern:**
```python
from datetime import datetime, timezone

# Create timestamp
now = datetime.now(timezone.utc).replace(microsecond=0).isoformat() + "Z"

# Parse timestamp
dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
if dt.tzinfo is None:
    dt = dt.replace(tzinfo=timezone.utc)
```

### Per-User Timezone (Not Implemented)

**Current Limitation:**
- No per-user timezone support
- All times displayed in UTC (or server timezone)
- No timezone conversion for display

**Proposed Implementation (Future):**
```python
# Store user timezone in conversation meta
conversation_meta["user_timezone"] = "Asia/Bangkok"  # IANA timezone

# Convert for display
from zoneinfo import ZoneInfo
user_tz = ZoneInfo(conversation_meta.get("user_timezone", "UTC"))
local_time = utc_time.astimezone(user_tz)
```

**Service Date Calculation:**
- Currently uses `created_at + 1 day` as placeholder
- Should use `preferred_window` + actual scheduling
- No timezone conversion applied

**Code Reference:**
```python
# src/ae/chat_automation.py - _on_booking_request_confirmed()
service_date = datetime.fromisoformat(booking.created_at.replace("Z", "+00:00"))
service_date = service_date.replace(tzinfo=None) if service_date.tzinfo else service_date
# Uses UTC, no conversion
```

---

## Retry Policy

### Hook Retry System

**File:** `src/ae/repo_hook_retries.py`  
**File:** `src/ae/jobs/hook_retry_worker.py`

**Purpose:** Retry failed hook deliveries (chat automation, event handlers)

### Retry Configuration

**Default Values:**
- `max_attempts: int = 6` - Maximum retry attempts
- `delay_seconds: int = 60` - Base delay between retries

**Exponential Backoff:**
```python
# Delay calculation: delay_seconds * (2 ** (attempt - 1))
# Attempt 1: 60 seconds (1 minute)
# Attempt 2: 120 seconds (2 minutes)
# Attempt 3: 240 seconds (4 minutes)
# Attempt 4: 480 seconds (8 minutes)
# Attempt 5: 960 seconds (16 minutes)
# Attempt 6: 1920 seconds (32 minutes)
```

**Code Reference:**
```python
def enqueue_hook_retry(
    db_path: str,
    *,
    event_id: str,
    hook_name: str,
    topic: str,
    error: str,
    max_attempts: int = 6,
    delay_seconds: int = 60,
) -> HookRetry:
    attempt_next = 1
    next_at = now + timedelta(seconds=int(delay_seconds) * (2 ** (attempt_next - 1)))
    # ...
```

### Retry Status

**Status Values:**
- `"pending"` - Retry scheduled, not yet attempted
- `"succeeded"` - Retry succeeded
- `"dead"` - Max attempts reached, retry abandoned

**Code Reference:**
```python
# src/ae/jobs/hook_retry_worker.py
if r.attempt >= r.max_attempts:
    mark_hook_retry(db_path, r.retry_id, status="dead", error=err)
else:
    # Increment attempt + schedule next (exponential backoff)
    enqueue_hook_retry(
        db_path,
        event_id=r.event_id,
        hook_name=r.hook_name,
        topic=r.topic,
        error=err,
        max_attempts=r.max_attempts,
        delay_seconds=60,  # Base delay
    )
```

### Dead Letter Behavior

**Current Implementation:**
- Retries marked as `"dead"` after `max_attempts` reached
- No dead letter queue - retries simply abandoned
- Error stored in `last_error` field (max 2000 chars)

**Database Schema:**
```sql
CREATE TABLE IF NOT EXISTS hook_retries (
    retry_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    hook_name TEXT NOT NULL,
    topic TEXT NOT NULL,
    attempt INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 6,
    status TEXT NOT NULL,  -- "pending" | "succeeded" | "dead"
    next_attempt_at TEXT NOT NULL,
    last_error TEXT,  -- Max 2000 chars
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

**Query Dead Retries:**
```python
dead_retries = list_hook_retries(db_path, status="dead", limit=100)
```

### Telegram Message Delivery Retry

**Current Implementation:**
- **No retry mechanism** - Best-effort delivery
- Failures logged but not retried
- Messages stored in database even if delivery fails

**Code Reference:**
```python
# src/ae/chat_automation.py - run_due_chat_automations()
try:
    from .telegram_delivery import send_message
    send_message(db_path, a.conversation_id, body)
except Exception:
    # Best-effort: don't fail if Telegram delivery fails
    pass

# Message still stored even if delivery fails
insert_message(db_path, conversation_id=a.conversation_id, direction="outbound", text=body, ...)
```

**Proposed Enhancement (Not Implemented):**
- Add retry mechanism for failed Telegram deliveries
- Use hook retry system for message delivery
- Store failed messages for manual retry

---

## Traffic Expectations & SQLite Sizing

### Current Assumptions

**File:** `ops/ASSUMPTION_LEDGER.md`

**A-0021 — SQLite remains the default store**
- **Assumption:** Most deployments run single-process SQLite (WAL) and accept its constraints.
- **Risk:** Multi-worker deployments can cause lock contention, and backup/restore needs discipline.
- **Mitigation:** Use edge rate limits; keep a single worker for console; implement Postgres adapter in a future patch.

**A-0024 — Single shared SQLite volume is sufficient**
- **Assumption:** Console + Public can safely share a single SQLite file on a docker volume with low write contention.
- **Risk:** Higher concurrency can introduce lock contention and latency spikes.
- **Mitigation:** Keep one worker per service; prefer WAL mode; move to Postgres adapter when traffic requires it.

### Rate Limiting Configuration

**Public API Rate Limits:**

**File:** `src/ae/public_guard.py`
```python
# Default values
AE_LEAD_RL_PER_MIN = 30  # Requests per minute
AE_LEAD_RL_BURST = 60    # Burst capacity

# Token bucket algorithm
# Refill rate: 30 tokens/minute = 0.5 tokens/second
# Burst: 60 tokens
```

**Abuse Controls Middleware:**

**File:** `src/ae/abuse_controls.py`
```python
# Default values
AE_RATE_LIMIT_RPS = 1.5      # Requests per second
AE_RATE_LIMIT_BURST = 10     # Burst capacity
AE_MAX_BODY_BYTES = 1_000_000  # 1MB max body size

# Per-route costs
AE_RL_COST_LEAD_INTAKE = 3.0   # Lead intake costs 3 tokens
AE_RL_COST_ADMIN = 1.5         # Admin routes cost 1.5 tokens
AE_RL_COST_DEFAULT = 1.0       # Default cost 1 token
# /metrics and /health cost 0.2 tokens
```

### SQLite Concurrency Limits

**WAL Mode:**
- SQLite WAL (Write-Ahead Logging) mode supports concurrent readers
- Single writer at a time
- Multiple readers can read while writer is active

**Lock Contention:**
- **Read locks:** Shared, non-blocking
- **Write locks:** Exclusive, blocks other writers
- **Checkpoint:** Periodic WAL checkpoint (can cause brief lock)

**Recommended Configuration:**
- **Single writer process** (console API)
- **Multiple reader processes** (public API, bots)
- **WAL mode enabled** (default in SQLite 3.7+)

**Code Reference:**
```python
# src/ae/db.py - connect()
con = sqlite3.connect(db_path)
con.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode
```

### Traffic Expectations

**Current Design Targets:**

**Lead Intake:**
- **Rate limit:** 30 requests/minute per IP (coarse /24)
- **Burst:** 60 requests
- **Expected:** < 10 leads/minute typical, < 100 leads/minute peak

**Telegram Bot:**
- **Polling:** 10-second intervals
- **Concurrent workers:** 1 per bot (customer + vendor = 2 workers)
- **Expected:** < 100 messages/minute per bot

**Moneyboard API:**
- **Rate limit:** 1.5 RPS (90 requests/minute)
- **Burst:** 10 requests
- **Expected:** < 10 requests/minute typical

**Chat Automation:**
- **Runner:** Processes up to 50 automations per run
- **Frequency:** Every minute (or on-demand)
- **Expected:** < 100 automations/minute

### SQLite Risk Sizing

**Database Size Limits:**
- **Theoretical:** Up to 281 TB (SQLite 3.32.0+)
- **Practical:** < 100 GB recommended for performance
- **WAL file:** Grows until checkpoint (can be large)

**Concurrent Workers:**
- **Recommended:** 1 writer, N readers (N < 10)
- **Risk:** Lock contention increases with more writers
- **Mitigation:** Single writer process, use read replicas if needed

**Write Contention:**
- **Lead intake:** Low (writes only on form submission)
- **Booking updates:** Medium (vendor bot + moneyboard)
- **Chat messages:** High (every message stored)
- **Chat automations:** Low (scheduled, not frequent)

**Performance Considerations:**
- **Indexes:** Critical for fast lookups (already implemented)
- **VACUUM:** Periodic cleanup recommended (not automated)
- **Checkpoint:** WAL checkpoint frequency affects write performance

**Migration Trigger:**
- **Postgres migration:** Recommended when:
  - Database size > 10 GB
  - Write contention > 10 writes/second sustained
  - Need for multi-writer concurrency
  - Need for horizontal scaling

**Code Reference:**
```python
# ops/ASSUMPTION_LEDGER.md - A-0021
# SQLite remains the default store until Postgres adapter is implemented
# Assumption: Most deployments run single-process SQLite (WAL) and accept its constraints.
# Risk: Multi-worker deployments can cause lock contention
# Mitigation: Use edge rate limits; keep a single worker for console
```

---

## Summary

### Status Enums
- **Lead:** `new`, `spam`, `contacted`, `qualified`, `converted`, `lost`
- **Booking:** `requested`, `deposit_requested`, `confirmed`, `completed`, `closed`, `cancelled`
- **Payment Intent:** `requested`, `paid`
- **Payment:** `pending`, `authorized`, `captured`, `failed`, `cancelled`, `refunded`

### Transition Rules
- **Booking:** `requested` → `deposit_requested` → `confirmed` → `completed` → `closed`
- **Payment Intent:** `requested` → `paid` (triggers booking confirmation)
- **Prerequisites:** Booking must be `deposit_requested` before `/confirm`

### Vendor Bot Auth
- **Current:** No authentication - any Telegram user can use commands
- **Storage:** `vendor_chat_id` in channel meta for notifications
- **Risk:** High - implement allowlist for production

### Timezone Policy
- **Current:** Single timezone (UTC) - all timestamps in UTC
- **Storage:** ISO-8601 UTC strings (`YYYY-MM-DDTHH:MM:SSZ`)
- **Future:** Per-user timezone not implemented

### Retry Policy
- **Max Attempts:** 6
- **Backoff:** Exponential (60s * 2^(attempt-1))
- **Dead Letter:** Marked as `"dead"` after max attempts, no queue

### Traffic Expectations
- **Lead Intake:** < 30/minute (rate limited)
- **Telegram Bot:** < 100 messages/minute per bot
- **SQLite:** Single writer, multiple readers, WAL mode
- **Migration:** Postgres when > 10 GB or > 10 writes/second sustained

---

**End of Document**
