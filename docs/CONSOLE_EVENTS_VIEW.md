# Viewing Events in Admin Console

## Quick Answer

**Yes, event tracking is now reflected in the admin console!** However, you need to **restart the console server** for the new endpoint to be available.

## What Was Added

1. **API Endpoint**: `GET /api/events?db=acq.db&page_id=p1&limit=200`
2. **Console UI**: New "Event Tracking" section
3. **Quick Action**: "Load events" button

## How to Use

### Step 1: Restart Console Server

The console server needs to be restarted to load the new route:

```powershell
# Stop the current console server (Ctrl+C)
# Then restart it:
$env:PYTHONPATH="src"
python -m ae.console_app
# Or: uvicorn ae.console_app:app --host 127.0.0.1 --port 8000
```

### Step 2: Open Console

Navigate to: `http://localhost:8000/console`

### Step 3: Load Events

**Option A: Quick Actions**
- Click "Load events" button in Quick Actions section

**Option B: Event Tracking Section**
- Scroll to "Event Tracking" section
- Optionally enter a `page_id` to filter
- Click "Load Events" button

## What You'll See

The events section displays:

1. **Summary Statistics**:
   ```
   Total: 5 events
   Browser: 2 | CLI: 3
   
   By type:
     call_click: 2
     quote_submit: 2
     thank_you_view: 1
   ```

2. **Full Event List** (JSON format):
   - `event_id`: Unique event identifier
   - `timestamp`: When event occurred
   - `page_id`: Which page triggered it
   - `event_name`: Event type (`call_click`, `quote_submit`, `thank_you_view`)
   - `params_json`: Event parameters including:
     - `url`: Page URL (browser events only)
     - `referrer`: Referrer URL (browser events only)
     - `utm_*`: UTM parameters (if present)

## Troubleshooting

### "Not Found" Error

**Cause**: Console server hasn't been restarted after adding the new route.

**Fix**: Restart the console server (see Step 1 above).

### No Events Shown

**Possible causes**:
1. No events recorded yet
2. Wrong `page_id` filter
3. Database path incorrect

**Check**:
```powershell
$env:PYTHONPATH="src"
python -c "from ae import repo; events = repo.list_events('acq.db'); print(f'Total events: {len(events)}')"
```

### Events Don't Update

- Click "Load Events" again to refresh
- Events are shown most recent first
- Default limit is 200 events

## API Endpoint Details

**Endpoint**: `GET /api/events`

**Query Parameters**:
- `db` (required): Database path (e.g., `acq.db`)
- `page_id` (optional): Filter by page ID
- `limit` (optional): Max events to return (default: 200)

**Response**:
```json
{
  "count": 5,
  "items": [
    {
      "event_id": "ev_abc123",
      "timestamp": "2026-02-06T07:36:14.207748",
      "page_id": "p1",
      "event_name": "call_click",
      "params_json": {
        "url": "http://localhost:8080/index.html",
        "referrer": null,
        "utm_source": "google"
      }
    }
  ]
}
```

## Summary

✅ **Event tracking IS reflected in admin console**  
⚠️ **Requires console server restart** to load new route  
📊 **Shows summary + full event details**  
🔍 **Supports filtering by page_id**
