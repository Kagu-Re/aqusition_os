# Event Tracking Verification Summary

## Quick Answer

To confirm tracking is working, you need to verify that **browser-recorded events** (not just CLI-recorded events) are being stored in the database.

## The Problem

You mentioned "it's listing 3 events that we added to page configuration" - these are likely CLI-recorded events (added via `record-event` command), not browser-recorded events from actual page interactions.

## How to Distinguish

### CLI-Recorded Events (Test/Setup)
- `params_json` contains only: `{"test":true}` or similar
- No `url`, `referrer`, or browser-specific fields
- Created via: `python -m ae.cli record-event`

### Browser-Recorded Events (Real Tracking)
- `params_json` contains:
  - `url`: Full page URL (e.g., `"http://localhost:8080/index.html"`)
  - `referrer`: Referrer URL or `null`
  - `timestamp`: ISO timestamp from JavaScript
  - `utm_*`: UTM parameters (if present in URL)
- Created via: User interaction → JavaScript → API → Database

## Verification Steps

### 1. Check Current Events

```bash
python -c "
from ae import repo
import json

events = repo.list_events('acq.db', 'p1')
print(f'Total events: {len(events)}')

# Categorize events
browser = [e for e in events if 'url' in e.params_json or 'referrer' in e.params_json]
cli = [e for e in events if 'url' not in e.params_json and 'referrer' not in e.params_json]

print(f'Browser events: {len(browser)}')
print(f'CLI events: {len(cli)}')

if browser:
    print('\nBrowser events:')
    for e in browser:
        print(f'  - {e.event_name} at {e.timestamp}')
        print(f'    URL: {e.params_json.get(\"url\", \"N/A\")}')
"
```

### 2. Test Browser Tracking

1. **Start public API** (if not running):
   ```bash
   python -m ae.public_api
   # Or: uvicorn ae.public_api:app --port 8001
   ```

2. **Serve HTML page**:
   ```bash
   cd exports/static_site/p1
   python -m http.server 8080
   ```

3. **Open in browser**: `http://localhost:8080/index.html`

4. **Click buttons**: Click "Book now" and "Get a quote"

5. **Check for new events**:
   ```bash
   python -c "
   from ae import repo
   events = repo.list_events('acq.db', 'p1')
   browser_events = [e for e in events if 'url' in e.params_json]
   print(f'Browser events: {len(browser_events)}')
   for e in browser_events[-3:]:  # Last 3
       print(f'  {e.event_name}: {e.params_json.get(\"url\")}')
   "
   ```

### 3. Automated Verification

Use the verification script:

```bash
python ops/scripts/verify_tracking.py --db acq.db --page-id p1
```

This will:
- ✅ Check HTML has tracking JavaScript
- ✅ Verify API endpoint is accessible
- ✅ Test API endpoint directly
- ✅ Distinguish browser vs CLI events
- ✅ Check validation status

## Expected Results

### ✅ Tracking is Working If:

1. **HTML includes tracking JavaScript**
   - Check: `exports/static_site/p1/index.html` has `<script>` tag
   - Contains: `trackEvent` function, `PAGE_ID`, `API_BASE`

2. **API endpoint is accessible**
   - Check: `curl http://localhost:8001/health` returns `{"status":"ok"}`

3. **Browser events are recorded**
   - Check: New events appear after clicking buttons
   - Events have `url` and `referrer` in `params_json`

4. **Validation passes**
   - Check: `validate-page` command succeeds
   - All 3 required events exist (`call_click`, `quote_submit`, `thank_you_view`)

### ❌ Tracking is NOT Working If:

1. **No browser events**
   - Only CLI events exist (`{"test":true}` in params)
   - No events with `url` field

2. **API errors**
   - Browser console shows CORS errors
   - Network tab shows failed POST requests
   - API endpoint returns 404 or 500

3. **JavaScript errors**
   - Browser console shows JavaScript errors
   - `trackEvent` function not defined

## Data Flow Diagram

```
User clicks button
    ↓
JavaScript executes trackEvent()
    ↓
POST /v1/event?db=acq.db
    ↓
Public API receives request
    ↓
Service.record_event()
    ↓
Repository.insert_event()
    ↓
SQLite INSERT INTO events
    ↓
Event stored in database
    ↓
Validation checks events exist
```

## Operations Exchange Summary

| Operation | Input | Processing | Output |
|-----------|-------|------------|--------|
| **Browser Event** | User click → JS payload | API → Service → Repo → SQL | EventRecord in DB |
| **CLI Event** | CLI args | Service → Repo → SQL | EventRecord in DB |
| **Validation** | Page ID | Query DB → Check events | Boolean result |
| **List Events** | Page ID (optional) | Query DB → Parse JSON | List[EventRecord] |

## Next Steps

1. **Run verification script**: `python ops/scripts/verify_tracking.py`
2. **Test browser tracking**: Open page, click buttons, check events
3. **Review documentation**: See `docs/EVENT_TRACKING_OPERATIONS.md` for details
4. **Troubleshoot**: See `docs/VERIFY_TRACKING.md` for troubleshooting

## Related Documentation

- **Operations & Data Flow**: `docs/EVENT_TRACKING_OPERATIONS.md`
- **Step-by-Step Verification**: `docs/VERIFY_TRACKING.md`
- **How Tracking Works**: `docs/HOW_EVENT_TRACKING_WORKS.md`
