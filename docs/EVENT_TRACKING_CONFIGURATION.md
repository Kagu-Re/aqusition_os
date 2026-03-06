# Event Tracking Configuration & Client Event Map

## Current State: Mismatch Between Configuration and Implementation

### The Issue

There are **two different event vocabularies** in the system:

1. **Client Event Map** (from onboarding templates):
   - `page_view` - Page load
   - `view_content` - User engaged (scrolled, viewed pricing)
   - `generate_lead` - Form submit, WhatsApp click, call click
   - `booking` - Appointment confirmed

2. **System EventName Enum** (hardcoded in code):
   - `call_click` - Call button clicked
   - `quote_submit` - Quote form submitted
   - `thank_you_view` - Thank you page viewed

### How It Currently Works

**Tracking JavaScript** (hardcoded):
- Uses fixed event names: `call_click`, `quote_submit`, `thank_you_view`
- Not configurable per client
- Same for all pages

**Validation** (hardcoded):
- Requires: `call_click`, `quote_submit`, `thank_you_view`
- Defined in `src/ae/policies.py`: `REQUIRED_PAGE_EVENTS_V1`

**Client Event Map** (documentation only):
- Stored in `event_map_md` template
- Used for documentation/guidance
- **Not used** by tracking JavaScript
- **Not used** by validation

## Event Type Differences

### Current Implementation

All events are tracked **the same way**:
- Same API endpoint: `/v1/event`
- Same payload structure
- Same database storage
- Same validation logic

**No differences** between event types in terms of:
- How they're sent (all use `fetch` with same config)
- How they're stored (all go to same `events` table)
- How they're validated (all checked the same way)

### Event-Specific Behavior

The only differences are:
1. **Event name** (stored in `event_name` field)
2. **When they fire** (different triggers in JavaScript)
3. **What they represent** (semantic meaning)

## Does It Match Client Configuration?

**Short answer: No, not currently.**

### Current Behavior

1. **Client event map** (`event_map_md`) is:
   - Stored per client
   - Used for documentation
   - **Not used** by tracking code

2. **Tracking JavaScript** uses:
   - Hardcoded event names
   - Same for all clients
   - Not configurable

3. **Validation** uses:
   - Hardcoded event names
   - Same for all clients
   - Not configurable

### Example Mismatch

**Client Event Map** says:
```
- generate_lead (form submit, WhatsApp click, call click)
- booking (appointment confirmed)
```

**System Actually Tracks**:
```
- call_click (call button)
- quote_submit (form submit)
- thank_you_view (thank you page)
```

**Mapping** (conceptual):
- `generate_lead` ≈ `call_click` + `quote_submit`
- `booking` ≈ `thank_you_view` (proxy)

## Why This Design?

### Current Approach (Fixed Events)

**Pros**:
- Simple, predictable
- No configuration needed
- Consistent across all clients
- Easy to validate

**Cons**:
- Not flexible per client
- Event map is documentation-only
- Can't customize tracking per client needs

### Event Map Purpose (Current)

The client event map (`event_map_md`) serves as:
1. **Documentation** - What events mean for this client
2. **Guidance** - How to interpret events
3. **Planning** - What to track (conceptual)
4. **Not implementation** - Not used by code

## How Events Are Actually Used

### Analytics/Reporting

Events are aggregated by type:
- `call_click` + `quote_submit` = "leads"
- `thank_you_view` = "bookings" (proxy)

See `src/ae/adapters/analytics_db.py`:
```python
call_click = counts.get("call_click", 0)
quote_submit = counts.get("quote_submit", 0)
thank_you_view = counts.get("thank_you_view", 0)

leads = call_click + quote_submit
bookings = thank_you_view
```

### Validation

Validation checks for existence of all 3 events:
```python
REQUIRED_PAGE_EVENTS_V1 = {
    "call_click",
    "quote_submit", 
    "thank_you_view"
}
```

## Future Enhancement: Client-Specific Tracking

To make tracking match client configuration, you would need:

1. **Read event map** from client templates
2. **Generate tracking JavaScript** based on event map
3. **Customize validation** per client
4. **Map client events** to system events

**Example**:
- Client event map: `generate_lead`, `booking`
- System maps: `generate_lead` → `call_click` + `quote_submit`
- System maps: `booking` → `thank_you_view`

## Current Recommendation

**For now**:
- Use client event map as **documentation**
- Use system events (`call_click`, `quote_submit`, `thank_you_view`) for **tracking**
- Map conceptually: `generate_lead` = `call_click` + `quote_submit`

**For future**:
- Consider making tracking configurable per client
- Read event map and generate custom JavaScript
- Allow client-specific event names

## Summary

| Aspect | Client Event Map | System Events |
|--------|------------------|---------------|
| **Purpose** | Documentation/Guidance | Actual Tracking |
| **Storage** | `event_map_md` template | `EventName` enum |
| **Used By** | Operators (reference) | JavaScript, Validation |
| **Configurable** | Yes (per client) | No (hardcoded) |
| **Flexible** | Yes | No |

**Answer to your questions**:
1. **Does it differ for different event types?** No, all events tracked the same way
2. **Does it match client configuration?** No, tracking uses fixed events, not client event map
