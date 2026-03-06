# How Event Tracking Works

## The Problem

You asked: **"Since page is just an HTML file, how can we validate that test events work?"**

This is a great question! Here's how the system works:

## Current Architecture

### 1. Static HTML Pages
- Pages are published as **static HTML files**
- No server-side rendering
- No built-in tracking code (until now)

### 2. Event Recording
- Events are stored in the SQLite database (`events` table)
- Events can be recorded via:
  - **CLI**: `python -m ae.cli record-event`
  - **Public API**: `POST /v1/event` (new endpoint)

### 3. Validation Check
- Validation checks if events exist in database
- Requires: `call_click`, `quote_submit`, `thank_you_view`
- But HTML page had no way to send events!

## The Solution

I've added two components:

### 1. Public API Endpoint

**New endpoint**: `POST /v1/event`

Allows HTML pages to send events to the database:

```javascript
fetch('http://localhost:8001/v1/event?db=acq.db', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    page_id: 'p1',
    event_name: 'call_click',
    params: {utm_source: 'google', utm_campaign: 'test'}
  })
});
```

### 2. Tracking JavaScript in HTML

The publisher now automatically includes tracking JavaScript that:
- Sends events to the API endpoint
- Tracks page interactions (clicks, form submits)
- Captures UTM parameters
- Uses `sendBeacon` for reliability

## How It Works Now

### Step 1: Publish Page
```bash
python -m ae.cli publish-page --db acq.db --page-id p1
```

**What happens**:
- HTML is generated with embedded tracking JavaScript
- JavaScript includes:
  - API endpoint URL (from `AE_PUBLIC_API_URL` env var or default)
  - Page ID
  - Database parameter
  - Event tracking functions

### Step 2: HTML Page Loads

When someone visits the published HTML:
1. Page loads in browser
2. Tracking JavaScript executes
3. Events are sent to `/v1/event` endpoint
4. Events are stored in database

### Step 3: Events Recorded

Events are automatically recorded when:
- **Page loads**: Test event fired (for validation)
- **User clicks "Book now"**: `call_click` event
- **User clicks "Get a quote"**: `quote_submit` event
- **User reaches thank you page**: `thank_you_view` event

### Step 4: Validation Works

Now validation can check:
- ✅ Events exist in database (from real page interactions)
- ✅ Events have correct `page_id`
- ✅ Events have UTM parameters (if present)

## Configuration

### API Base URL

Set the public API URL via environment variable:
```bash
export AE_PUBLIC_API_URL="https://yourdomain.com/api"
```

Or it defaults to: `http://localhost:8001`

### Database Parameter

The tracking JavaScript includes the database name in the API call:
- Default: `acq.db`
- Can be overridden via context when publishing

## Testing Event Tracking

### Manual Test (CLI)
```bash
# Record test events manually
python -m ae.cli record-event --db acq.db --page-id p1 --event-name call_click
```

### Real Test (From HTML Page)

1. **Publish page** (includes tracking JS)
2. **Open HTML file** in browser
3. **Check browser console** for API calls
4. **Click buttons** to trigger events
5. **Verify events** in database:
   ```bash
   python -c "from ae import repo; events = repo.list_events('acq.db', 'p1'); print(f'Found {len(events)} events')"
   ```

### Check Events in Database

```bash
python -c "
from ae import repo
events = repo.list_events('acq.db', page_id='p1')
for e in events:
    print(f'{e.event_name}: {e.timestamp}')
"
```

## Event Flow Diagram

```
┌─────────────┐
│ HTML Page   │
│ (static)    │
└──────┬──────┘
       │
       │ JavaScript tracking code
       │ (embedded in HTML)
       ▼
┌─────────────┐
│ POST /v1/   │
│ event        │
└──────┬──────┘
       │
       │ Public API
       │ (FastAPI)
       ▼
┌─────────────┐
│ Database     │
│ (events)     │
└──────────────┘
```

## Why This Design?

### Static HTML Benefits
- ✅ Fast loading (no server processing)
- ✅ Can be deployed to CDN
- ✅ Works offline (with cached API calls)
- ✅ Simple hosting (just serve files)

### API-Based Tracking Benefits
- ✅ Centralized event storage
- ✅ Can validate events exist
- ✅ Can analyze events across pages
- ✅ Can integrate with other systems

### Trade-offs
- ⚠️ Requires public API to be accessible
- ⚠️ Events fail silently if API is down
- ⚠️ Requires CORS configuration for cross-origin

## Production Considerations

### 1. API Availability
- Public API must be running and accessible
- Consider fallback/retry logic in tracking JS
- Monitor API health

### 2. CORS Configuration
- Set `AE_PUBLIC_CORS_ORIGINS` environment variable
- Restrict to your domain(s) in production

### 3. Rate Limiting
- Public API has rate limiting built-in
- Prevents abuse/spam events

### 4. Privacy
- Events don't contain PII by default
- UTM parameters are captured (for attribution)
- Consider GDPR compliance for EU traffic

## Summary

**Before**: HTML page had no tracking → Events only via CLI → Validation required manual event recording

**After**: HTML page includes tracking JS → Events sent automatically → Validation checks real events from page interactions

The tracking JavaScript is now **automatically included** when you publish a page, so events will be recorded when users interact with the page!
