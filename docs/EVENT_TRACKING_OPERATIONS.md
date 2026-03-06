# Event Tracking Operations & Data Flow

## Overview

This document defines all operations involved in event tracking and how data flows through the system.

## System Components

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│ HTML Page   │────▶│ Public API   │────▶│ Service     │────▶│ Database     │
│ (Browser)   │     │ /v1/event    │     │ Layer       │     │ (SQLite)     │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
      │                    │                    │                   │
      │                    │                    │                   │
      │                    │                    │                   │
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│ CLI Command │────▶│ Service      │────▶│ Repository  │────▶│ events table │
│ record-event│     │ record_event │     │ insert_event│     │              │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
```

## Operation 1: Browser Event Tracking (HTML → API → DB)

### Flow Diagram
```
User Action → JavaScript → POST /v1/event → Service → Repository → Database
```

### Step-by-Step

1. **User Interaction** (Browser)
   - User clicks "Book now" button
   - User clicks "Get a quote" button
   - User submits form
   - User navigates to thank you page

2. **JavaScript Execution** (`exports/static_site/{page_id}/index.html`)
   - Event listener detects click/submit
   - Calls `trackEvent(eventName, params)`
   - Builds payload:
     ```javascript
     {
       page_id: "p1",
       event_name: "call_click",
       params: {
         utm_source: "google",
         utm_campaign: "test",
         timestamp: "2026-02-06T10:30:00.000Z",
         url: "http://localhost:8080/index.html",
         referrer: null
       }
     }
     ```
   - Sends via `navigator.sendBeacon()` or `fetch()`

3. **API Endpoint** (`src/ae/console_routes_events_public.py`)
   - Receives POST request at `/v1/event?db=acq.db`
   - Validates request (rate limiting)
   - Parses JSON payload
   - Extracts `page_id`, `event_name`, `params`
   - Validates `event_name` against `EventName` enum

4. **Service Layer** (`src/ae/service.py`)
   - Calls `service.record_event()`
   - Creates `EventRecord` object:
     ```python
     EventRecord(
       event_id="ev_...",
       timestamp=datetime.utcnow(),
       page_id="p1",
       event_name=EventName.call_click,
       params_json={...}
     )
     ```

5. **Repository Layer** (`src/ae/repo_events.py`)
   - Calls `repo.insert_event()`
   - Opens database connection
   - Executes SQL:
     ```sql
     INSERT INTO events(event_id, timestamp, page_id, event_name, params_json)
     VALUES(?, ?, ?, ?, ?)
     ```
   - Commits transaction

6. **Database** (`acq.db`)
   - Stores in `events` table:
     ```sql
     CREATE TABLE events (
       event_id TEXT PRIMARY KEY,
       timestamp TEXT NOT NULL,
       page_id TEXT NOT NULL,
       event_name TEXT NOT NULL,
       params_json TEXT NOT NULL
     );
     ```

### Data Fields

**Request Payload** (from browser):
```json
{
  "page_id": "p1",
  "event_name": "call_click",
  "params": {
    "utm_source": "google",
    "utm_medium": "cpc",
    "utm_campaign": "test-campaign",
    "timestamp": "2026-02-06T10:30:00.000Z",
    "url": "http://localhost:8080/index.html",
    "referrer": null
  }
}
```

**Database Record**:
```sql
event_id: "ev_abc123"
timestamp: "2026-02-06T10:30:00.000000"
page_id: "p1"
event_name: "call_click"
params_json: '{"utm_source":"google","utm_medium":"cpc","utm_campaign":"test-campaign","timestamp":"2026-02-06T10:30:00.000Z","url":"http://localhost:8080/index.html","referrer":null}'
```

## Operation 2: CLI Event Recording (CLI → Service → DB)

### Flow Diagram
```
CLI Command → Service → Repository → Database
```

### Step-by-Step

1. **CLI Command** (`src/ae/cli.py`)
   ```bash
   python -m ae.cli record-event \
     --db acq.db \
     --page-id p1 \
     --event-name call_click \
     --params-json '{"test":true}'
   ```

2. **Service Layer** (`src/ae/service.py`)
   - Same as Operation 1, step 4
   - Creates `EventRecord` with CLI-provided params

3. **Repository Layer** (`src/ae/repo_events.py`)
   - Same as Operation 1, step 5

4. **Database** (`acq.db`)
   - Same as Operation 1, step 6

### Data Fields

**CLI Input**:
```bash
--params-json '{"test":true}'
```

**Database Record**:
```sql
event_id: "ev_xyz789"
timestamp: "2026-02-06T10:35:00.000000"
page_id: "p1"
event_name: "call_click"
params_json: '{"test":true}'
```

## Operation 3: Event Validation (DB → Service → Validation)

### Flow Diagram
```
Validation Request → Repository → Database Query → Check Results
```

### Step-by-Step

1. **Validation Request** (`src/ae/service.py`)
   - Called during `validate_page()` or `publish_page()`
   - Checks `has_validated_events()`

2. **Repository Query** (`src/ae/repo_events.py`)
   ```python
   def has_validated_events(db_path: str, page_id: str) -> bool:
       rows = db.fetchall(
           "SELECT event_name, COUNT(*) as c FROM events WHERE page_id=? GROUP BY event_name",
           (page_id,)
       )
       got = {r["event_name"] for r in rows}
       return {"call_click", "quote_submit", "thank_you_view"}.issubset(got)
   ```

3. **Database Query**
   ```sql
   SELECT event_name, COUNT(*) as c 
   FROM events 
   WHERE page_id='p1' 
   GROUP BY event_name
   ```

4. **Validation Result**
   - Returns `True` if all 3 required events exist
   - Returns `False` if any are missing

## Operation 4: Event Listing (DB → Repository → API/CLI)

### Flow Diagram
```
List Request → Repository → Database Query → Return Events
```

### Step-by-Step

1. **List Request**
   - Via CLI: `python -c "from ae import repo; repo.list_events('acq.db', 'p1')"`
   - Via API: (if endpoint exists)

2. **Repository Query** (`src/ae/repo_events.py`)
   ```python
   def list_events(db_path: str, page_id: str | None = None) -> List[EventRecord]:
       if page_id:
           rows = db.fetchall(
               "SELECT * FROM events WHERE page_id=? ORDER BY timestamp ASC",
               (page_id,)
           )
       else:
           rows = db.fetchall("SELECT * FROM events ORDER BY timestamp ASC")
       # Convert rows to EventRecord objects
   ```

3. **Database Query**
   ```sql
   SELECT * FROM events WHERE page_id='p1' ORDER BY timestamp ASC
   ```

4. **Return Results**
   - List of `EventRecord` objects
   - Each with `event_id`, `timestamp`, `page_id`, `event_name`, `params_json`

## Data Exchange Summary

### Input Sources

| Source | Method | Endpoint/Command | Payload Format |
|--------|--------|------------------|----------------|
| Browser | POST | `/v1/event?db=acq.db` | JSON: `{page_id, event_name, params}` |
| CLI | Command | `record-event` | CLI args: `--page-id`, `--event-name`, `--params-json` |

### Processing Layers

| Layer | Function | Input | Output |
|-------|----------|-------|--------|
| API Router | `record_event_public()` | `EventIn` (Pydantic) | HTTP Response |
| Service | `record_event()` | `db_path, page_id, event_name, params` | `EventRecord` |
| Repository | `insert_event()` | `EventRecord` | SQL INSERT |
| Database | SQLite | SQL + params | Stored row |

### Database Schema

```sql
CREATE TABLE events (
  event_id TEXT PRIMARY KEY,        -- Unique ID (e.g., "ev_abc123")
  timestamp TEXT NOT NULL,           -- ISO format datetime
  page_id TEXT NOT NULL,             -- Page identifier (e.g., "p1")
  event_name TEXT NOT NULL,          -- Event type (e.g., "call_click")
  params_json TEXT NOT NULL          -- JSON object with event data
);
```

### Output Formats

| Output | Format | Example |
|--------|--------|---------|
| API Response | JSON | `{"status":"ok","event_id":"ev_...","event_name":"call_click","page_id":"p1"}` |
| Database Row | SQL Row | `(event_id, timestamp, page_id, event_name, params_json)` |
| Python Object | `EventRecord` | `EventRecord(event_id="ev_...", timestamp=datetime(...), ...)` |

## Distinguishing Event Sources

### Browser-Recorded Events
**Characteristics**:
- `params_json` contains:
  - `url`: Full page URL
  - `referrer`: Referrer URL (or null)
  - `timestamp`: ISO timestamp from JavaScript
  - `utm_*`: UTM parameters (if present in URL)
- `timestamp` matches browser's local time
- Often has UTM parameters

**Example**:
```json
{
  "event_id": "ev_abc123",
  "timestamp": "2026-02-06T10:30:00.000000",
  "page_id": "p1",
  "event_name": "call_click",
  "params_json": {
    "utm_source": "google",
    "utm_campaign": "test",
    "timestamp": "2026-02-06T10:30:00.000Z",
    "url": "http://localhost:8080/index.html",
    "referrer": null
  }
}
```

### CLI-Recorded Events
**Characteristics**:
- `params_json` is minimal (often `{"test":true}`)
- No `url`, `referrer`, or browser-specific fields
- `timestamp` is server time (UTC)
- Usually for testing/validation

**Example**:
```json
{
  "event_id": "ev_xyz789",
  "timestamp": "2026-02-06T10:35:00.000000",
  "page_id": "p1",
  "event_name": "call_click",
  "params_json": {
    "test": true
  }
}
```

## Verification Checklist

To confirm tracking is working:

- [ ] **HTML has tracking JavaScript**
  - Check `exports/static_site/{page_id}/index.html`
  - Look for `<script>` tag with tracking code
  - Verify `PAGE_ID`, `API_BASE`, `DB_PARAM` are set correctly

- [ ] **Public API is running**
  - Check `http://localhost:8001/v1/event` is accessible
  - Verify CORS allows browser requests

- [ ] **Database is writable**
  - Check `acq.db` exists and is writable
  - Verify `events` table exists

- [ ] **Events are recorded**
  - Open HTML page in browser
  - Click buttons/interact with page
  - Check database for new events
  - Verify events have `url` and `referrer` in `params_json`

- [ ] **Validation works**
  - Run `validate-page` command
  - Should pass if all 3 events exist
  - Should fail if events are missing

## Next Steps

See `docs/VERIFY_TRACKING.md` for step-by-step verification instructions.
