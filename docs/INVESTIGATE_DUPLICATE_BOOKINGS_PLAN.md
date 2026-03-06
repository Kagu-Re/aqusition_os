# Investigation Plan: Duplicate Booking Creation

## Problem Statement
Bookings are being created multiple times. Need to:
1. Investigate why bookings fire multiple times
2. Determine if we should remove booking information on dev server start

## Current State Analysis

### Booking Creation Flow
- `handle_timeslot_selection()` creates bookings via `create_booking_request()`
- Booking IDs are generated with millisecond timestamps: `br_telegram_{chat_id}_{timestamp}`
- No deduplication check before creating bookings
- Conversation state is cleared AFTER booking creation (lines 751-762)

### Existing Protections
- `/start` command cooldown (3 seconds)
- Deep link deduplication (5 seconds)
- Active conversation check (prevents new `/start` if `pending_package_id` exists)
- `scripts/runbooks/clear_stale_conversations.py` clears conversation state on dev server start

### Potential Root Causes
1. **Race condition**: Multiple calls to `handle_timeslot_selection()` before state is cleared
2. **Duplicate Telegram messages**: Telegram API sending duplicate updates
3. **Message deduplication gap**: Only message IDs are tracked, but rapid identical messages could slip through
4. **No booking-level deduplication**: Even if conversation state exists, booking creation isn't checked for duplicates

## Investigation Plan

### Phase 1: Instrumentation & Data Collection
1. **Add logging to `handle_timeslot_selection()`**:
   - Log function entry with parameters (chat_id, package_id, timeslot_input)
   - Log before booking creation (lead_id, request_id)
   - Log after booking creation (success/failure, booking_id)
   - Log conversation state before/after clearing

2. **Add logging to `handle_message()`**:
   - Log when timeslot selection is triggered
   - Log message deduplication checks
   - Log conversation state retrieval

3. **Add logging to `create_booking_request()`**:
   - Log when booking is about to be created
   - Log if duplicate request_id detected (database constraint)

### Phase 2: Add Deduplication Logic
1. **Check for duplicate bookings before creation**:
   - Query `booking_requests` table for existing bookings with:
     - Same `lead_id`
     - Same `package_id`  
     - Same `preferred_window`
     - Created within last 30 seconds
   - If duplicate found, return existing booking instead of creating new one

2. **Add booking creation cooldown**:
   - Track last booking creation time per `chat_id` in instance memory
   - Block new bookings if last booking was created within 10 seconds

3. **Clear conversation state BEFORE booking creation**:
   - Move state clearing to happen immediately after timeslot validation
   - This prevents race conditions where multiple calls see the same `pending_package_id`

### Phase 3: Dev Server Startup Cleanup
1. **Option A: Clear booking requests** (recommended for dev):
   - Create `clear_dev_booking_requests.py` script
   - Delete all booking requests with status "requested" on dev server start
   - Add to `start_local_dev.ps1`

2. **Option B: Keep booking requests, only clear conversation state** (current):
   - Keep existing `scripts/runbooks/clear_stale_conversations.py` behavior
   - Only clear conversation state, preserve booking history

### Phase 4: Verification
1. Test with rapid timeslot selections
2. Test with duplicate Telegram messages
3. Verify no duplicate bookings are created
4. Verify conversation state is properly cleared
5. Verify dev server startup clears stale state

## Implementation Details

### Files to Modify
1. `src/ae/telegram_polling.py`:
   - Add instrumentation logs to `handle_timeslot_selection()`
   - Add deduplication check before `create_booking_request()`
   - Add booking creation cooldown tracking
   - Move conversation state clearing earlier in flow

2. `src/ae/repo_booking_requests.py`:
   - Add `get_recent_booking_request()` function to check for duplicates
   - Add instrumentation logs to `create_booking_request()`

3. `start_local_dev.ps1` (optional):
   - Add call to clear booking requests script if Option A chosen

### New Files
1. `clear_dev_booking_requests.py` (optional, if Option A):
   - Script to delete "requested" bookings on dev server start

## Success Criteria
- No duplicate bookings created for same lead_id + package_id + timeslot within 30 seconds
- Logs show clear flow of booking creation attempts
- Dev server startup clears stale state appropriately
- User can still create legitimate bookings normally

## Notes
- Keep instrumentation logs active during verification
- Remove logs only after confirmed success
- Prefer defensive checks (deduplication) over aggressive blocking
- Maintain backward compatibility with existing booking flow
