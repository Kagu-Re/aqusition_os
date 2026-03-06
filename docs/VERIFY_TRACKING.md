# How to Verify Event Tracking is Working

## Quick Test

This guide shows you how to confirm that browser-based event tracking is correctly integrated with the database.

## Prerequisites

- Page published with tracking JavaScript
- Public API running (`http://localhost:8001`)
- Database accessible (`acq.db`)

## Step 1: Check HTML Has Tracking Code

Verify the published HTML includes tracking JavaScript:

```bash
# Check if tracking script exists
grep -A 5 "Acquisition Engine Tracking" exports/static_site/p1/index.html
```

**Expected**: Should see JavaScript code with `trackEvent` function.

## Step 2: Count Existing Events (Baseline)

Get baseline count of events before testing:

```bash
python -c "
from ae import repo
events = repo.list_events('acq.db', 'p1')
print(f'Current events: {len(events)}')
for e in events:
    print(f'  - {e.event_name} at {e.timestamp}')
"
```

**Note**: These might be CLI-recorded events (have `{"test":true}` in params).

## Step 3: Start Public API (if not running)

The tracking JavaScript needs the API to be accessible:

```bash
# Start public API server
python -m ae.public_api
# Or via uvicorn
uvicorn ae.public_api:app --port 8001
```

**Verify**: `curl http://localhost:8001/health` should return `{"status":"ok"}`

## Step 4: Open HTML Page in Browser

1. **Serve the HTML file** (choose one method):

   **Option A: Direct file open**
   - Navigate to `exports/static_site/p1/index.html` in File Explorer
   - Double-click to open in browser
   - Note: API calls may fail due to CORS if opened as `file://`

   **Option B: Local HTTP server** (recommended)
   ```bash
   cd exports/static_site/p1
   python -m http.server 8080
   ```
   - Open: `http://localhost:8080/index.html`

   **Option C: Serve entire exports directory**
   ```bash
   cd exports/static_site
   python -m http.server 8080
   ```
   - Open: `http://localhost:8080/p1/index.html`

2. **Open browser developer tools**
   - Press `F12` or right-click → Inspect
   - Go to **Console** tab
   - Go to **Network** tab (to see API calls)

## Step 5: Interact with Page

Click the buttons to trigger events:

1. **Click "Book now"** → Should trigger `call_click` event
2. **Click "Get a quote"** → Should trigger `quote_submit` event

**Check browser console**:
- Should see no errors
- API calls should appear in Network tab
- Look for POST requests to `/v1/event`

## Step 6: Verify Events Were Recorded

Check the database for new events:

```bash
python -c "
from ae import repo
import json

events = repo.list_events('acq.db', 'p1')
print(f'Total events: {len(events)}')
print()

# Show recent events with details
for e in sorted(events, key=lambda x: x.timestamp, reverse=True)[:5]:
    print(f'Event: {e.event_name}')
    print(f'  ID: {e.event_id}')
    print(f'  Time: {e.timestamp}')
    print(f'  Params: {json.dumps(e.params_json, indent=2)}')
    print()
"
```

**Look for**:
- ✅ Events with `"url"` in `params_json` → Browser-recorded
- ✅ Events with `"referrer"` in `params_json` → Browser-recorded
- ✅ Events with UTM parameters → Browser-recorded
- ⚠️ Events with only `{"test":true}` → CLI-recorded (old)

## Step 7: Verify Event Source

Distinguish browser events from CLI events:

```bash
python -c "
from ae import repo
import json

events = repo.list_events('acq.db', 'p1')

browser_events = []
cli_events = []

for e in events:
    params = e.params_json
    if 'url' in params or 'referrer' in params:
        browser_events.append(e)
    else:
        cli_events.append(e)

print(f'Browser-recorded events: {len(browser_events)}')
print(f'CLI-recorded events: {len(cli_events)}')
print()

if browser_events:
    print('Browser events:')
    for e in browser_events:
        print(f'  - {e.event_name} at {e.timestamp}')
        if 'url' in e.params_json:
            print(f'    URL: {e.params_json[\"url\"]}')
print()

if cli_events:
    print('CLI events:')
    for e in cli_events:
        print(f'  - {e.event_name} at {e.timestamp}')
"
```

## Step 8: Test API Endpoint Directly

Verify the API endpoint works:

```bash
# Test with curl
curl -X POST http://localhost:8001/v1/event?db=acq.db \
  -H "Content-Type: application/json" \
  -d '{
    "page_id": "p1",
    "event_name": "call_click",
    "params": {
      "test": "api_test",
      "source": "curl"
    }
  }'
```

**Expected response**:
```json
{
  "status": "ok",
  "event_id": "ev_...",
  "event_name": "call_click",
  "page_id": "p1"
}
```

## Step 9: Verify Validation

Check that validation recognizes the events:

```bash
python -m ae.cli validate-page --db acq.db --page-id p1
```

**Expected**: Should pass if all 3 required events exist (`call_click`, `quote_submit`, `thank_you_view`).

## Troubleshooting

### No Events Recorded

**Check**:
1. **API is running**: `curl http://localhost:8001/health`
2. **CORS is configured**: Check `AE_PUBLIC_CORS_ORIGINS` env var
3. **Database is writable**: Check file permissions on `acq.db`
4. **Browser console errors**: Look for JavaScript errors
5. **Network tab**: Check if POST requests are being sent

**Common issues**:
- **CORS error**: API not allowing browser origin
  - Fix: Set `AE_PUBLIC_CORS_ORIGINS` or use same-origin hosting
- **404 on API**: Public API not running or wrong URL
  - Fix: Start API server, check `API_BASE` in HTML matches server URL
- **Database locked**: Another process has DB open
  - Fix: Close other connections, check for file locks

### Events Recorded but Validation Fails

**Check**:
1. **Event names match**: Must be exactly `call_click`, `quote_submit`, `thank_you_view`
2. **Page ID matches**: Events must have correct `page_id`
3. **Events exist**: Run `list_events` to verify

**Fix**:
- Ensure all 3 event types are recorded
- Check `has_validated_events()` logic in `src/ae/repo_events.py`

### Events Have Wrong Params

**Check**:
- Browser events should have `url`, `referrer`, `timestamp` in params
- CLI events might only have `{"test":true}`

**Fix**:
- Republish page to update tracking JavaScript
- Clear old CLI events if needed:
  ```sql
  DELETE FROM events WHERE page_id='p1' AND params_json='{"test":true}';
  ```

## Success Criteria

✅ **Tracking is working if**:
1. HTML page includes tracking JavaScript
2. Clicking buttons creates new events in database
3. New events have `url` and `referrer` in `params_json`
4. API endpoint accepts and records events
5. Validation passes with browser-recorded events

## Automated Verification Script

See `ops/scripts/verify_tracking.py` for an automated verification script.
