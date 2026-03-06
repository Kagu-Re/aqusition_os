# Database Integration & Bulk Updates Analysis

## Overview

This document analyzes the current database integration patterns, default states of each console tab, and proposes bulk update functionality for entities.

## Database Integration Patterns

### Repository Pattern

All database operations follow a consistent repository pattern:

**Location**: `src/ae/repo_*.py` modules

**Common Operations**:
- `create_*` / `upsert_*` - Create or update entity
- `get_*` - Get single entity by ID
- `list_*` - List entities with optional filters
- `update_*` - Update existing entity
- `delete_*` - Delete entity

**Database Connection Pattern**:
```python
con = db.connect(db_path)
try:
    # SQL operations
    con.execute(...)
    con.commit()
finally:
    con.close()
```

### Current Entities & Repositories

| Entity | Repository File | Key Functions | Bulk Ops Available |
|--------|----------------|---------------|---------------------|
| **Pages** | `repo_pages.py` | `upsert_page`, `get_page`, `list_pages`, `update_page_status` | ✅ validate, publish, pause |
| **Service Packages** | `repo_service_packages.py` | `create_package`, `get_package`, `list_packages`, `update_package`, `delete_package` | ❌ None |
| **Chat Channels** | `repo_chat_channels.py` | `upsert_chat_channel`, `get_chat_channel`, `list_chat_channels`, `delete_chat_channel` | ❌ None |
| **Clients** | `repo_clients.py` | `upsert_client`, `get_client`, `set_client_status` | ❌ None |
| **Leads** | `repo_leads.py` | `insert_lead`, `get_lead`, `list_leads`, `update_lead_outcome` | ❌ None |
| **Menus** | `repo_menus.py` | `upsert_menu`, `get_menu`, `list_menus` | ❌ None |

### Existing Bulk Operations (Pages Only)

**Location**: `src/ae/service.py`

**Functions**:
- `run_bulk_validate()` - Validate multiple pages
- `run_bulk_publish()` - Publish multiple pages
- `run_bulk_pause()` - Pause multiple pages

**Pattern**:
1. Create `BulkOp` record with selector criteria
2. Resolve target IDs from selector
3. Process each target sequentially
4. Update `BulkOp` with progress/results
5. Log activity

**Selector Pattern**:
```python
selector = {
    "page_ids": [...],  # Explicit list
    "page_status": "draft",  # Filter by status
    "client_id": "client1",  # Filter by client
    "template_id": "template1",  # Filter by template
    "geo_city": "Sydney",  # Filter by geo (via join)
    "limit": 200
}
```

## Default State Analysis by Tab

### 1. Dashboard (`/dashboard`)

**Default State**:
- Shows loading spinner in activity section
- Summary cards show "—" (dash) placeholders
- Auto-loads on page load:
  - KPIs (`loadKpis()`)
  - Activity (`loadActivity()`)
  - Summary metrics (leads count, revenue, ROAS, campaigns)

**Filters**: None (aggregate view)

**Data Sources**:
- `/api/leads?db=...&limit=1` - Lead count
- `/api/stats/roas?db=...` - Revenue/ROAS
- `/api/stats/campaigns?db=...` - Campaign count
- `/api/stats/kpis?db=...&day_from=...&day_to=...` - KPIs
- `/api/activity?db=...&limit=200` - Activity log

### 2. Landing Pages (`/landing-pages`)

**Default State**:
- Shows loading spinner: "Loading landing pages..."
- Form is empty (defaults: template_id="trade_lp", locale="en-AU", status="draft")
- Filters are empty
- Auto-loads on page load: `loadLandingPages()`

**Filters**:
- `filter_client_id` - Client ID filter
- `filter_template_id` - Template ID filter
- `filter_status` - Status dropdown (any/draft/live/paused)

**Data Sources**:
- `/api/pages?db=...&client_id=...&template_id=...&page_status=...` - List pages
- `/api/pages` (POST) - Create page
- `/api/pages/{page_id}/validate` (POST) - Validate page
- `/api/pages/{page_id}/publish` (POST) - Publish page

**Bulk Operations Available**: ✅ (via Quick Actions in main console)

### 3. Service Packages (`/service-packages`)

**Default State**:
- Shows loading spinner: "Loading service packages..."
- Form is empty
- Filters are empty
- Auto-loads on page load: `loadServicePackages()`

**Filters**:
- `filter_client_id` - Client ID filter
- `filter_active` - Active status (any/true/false)

**Data Sources**:
- `/api/service-packages?db=...&client_id=...&active=...` - List packages
- `/api/service-packages` (POST) - Create package
- `/api/service-packages/{package_id}` (PUT) - Update package
- `/api/service-packages/{package_id}` (DELETE) - Delete package

**Bulk Operations Available**: ❌ None

### 4. Bot Setup (`/bot-setup`)

**Default State**:
- Shows loading spinner: "Loading chat channels..."
- Form is empty
- Filters are empty
- Auto-loads on page load:
  - `loadChatChannels()`
  - `loadTelegramConfig()`

**Filters**:
- `filter_provider` - Provider dropdown (any/whatsapp/telegram/line/sms/other)

**Data Sources**:
- `/api/chat/channels?db=...&provider=...` - List channels
- `/api/chat/channels` (POST) - Create channel
- `/api/chat/channels/{channel_id}` (PUT) - Update channel
- `/api/chat/channels/{channel_id}` (DELETE) - Delete channel
- `/api/notify/config?db=...` - Telegram config

**Bulk Operations Available**: ❌ None

### 5. Reporting (`/reporting`)

**Default State**:
- Shows empty states for all sections:
  - KPI Cards: Empty
  - Campaign Performance: "Loading campaign data..."
  - Page Performance: "No page data loaded"
  - Revenue & ROAS: "No revenue data loaded"
- Filters have no defaults (empty)
- Does NOT auto-load (requires manual "Load Report" click)

**Filters**:
- `report_from` - From date (date picker)
- `report_to` - To date (date picker)
- `report_client_id` - Client ID filter
- `report_page_id` - Page ID filter
- `report_platform` - Platform dropdown (all/meta/google/other)

**Data Sources**:
- `/api/kpi/page/{page_id}?db=...&since_iso=...&platform=...` - Page KPIs
- `/api/kpi/client/{client_id}?db=...&since_iso=...&platform=...` - Client KPIs
- `/api/stats/campaigns?db=...&since_iso=...&until_iso=...` - Campaign stats
- `/api/pages?db=...` - Pages list

**Bulk Operations Available**: ❌ None (read-only)

### 6. Leads (`/leads`)

**Default State**:
- Shows loading spinner: "Loading leads..."
- Filters are empty
- Auto-loads on page load: `loadLeads()`

**Filters**:
- `leads_search` - Text search (name, email, phone, message)
- `leads_status` - Status dropdown (all/new/contacted/qualified/lost)
- `leads_booking_status` - Booking status (all/none/booked/paid/lost)
- `leads_date_from` - From date
- `leads_date_to` - To date

**Data Sources**:
- `/api/leads?db=...&limit=...&status=...&booking_status=...` - List leads
- `/api/leads/{lead_id}/outcome` (PUT) - Update lead outcome

**Bulk Operations Available**: ❌ None

### 7. Events (`/events`)

**Default State**:
- Shows loading spinner in events section
- Filter `events_page_id` is empty
- Auto-loads when section expanded: `loadEvents()`

**Filters**:
- `events_page_id` - Page ID filter

**Data Sources**:
- `/api/events?db=...&page_id=...&limit=200` - List events

**Bulk Operations Available**: ❌ None (read-only)

### 8. Activity (`/activity`)

**Default State**:
- Shows loading spinner: "Loading activity..."
- Auto-loads on page load: `loadActivity()`

**Filters**: None (shows recent activity)

**Data Sources**:
- `/api/activity?db=...&limit=200&action=...&entity_type=...&entity_id=...` - Activity log

**Bulk Operations Available**: ❌ None (read-only)

## Proposed Bulk Update Functionality

### Design Principles

1. **Consistent Pattern**: Follow existing bulk operations pattern for pages
2. **Selector-Based**: Use filters to select entities (not just explicit IDs)
3. **Dry-Run Mode**: Always support dry-run before execution
4. **Progress Tracking**: Update BulkOp record with progress
5. **Activity Logging**: Log all bulk operations

### Entity-Specific Bulk Operations

#### 1. Service Packages

**Bulk Actions**:
- `bulk_activate` - Set `active=true` for selected packages
- `bulk_deactivate` - Set `active=false` for selected packages
- `bulk_update_price` - Update price for selected packages
- `bulk_delete` - Delete selected packages

**Selector Criteria**:
```python
{
    "package_ids": [...],  # Explicit list
    "client_id": "...",  # Filter by client
    "active": true/false,  # Filter by active status
    "limit": 200
}
```

**Update Pattern**:
```python
# For each package:
existing = repo.get_package(db_path, package_id)
updated = ServicePackage(
    ...existing fields...,
    active=new_value,  # or price=new_price
    updated_at=datetime.utcnow()
)
repo.update_package(db_path, updated)
```

#### 2. Chat Channels

**Bulk Actions**:
- `bulk_update_provider` - Change provider for selected channels
- `bulk_update_meta` - Update meta_json for selected channels
- `bulk_delete` - Delete selected channels

**Selector Criteria**:
```python
{
    "channel_ids": [...],  # Explicit list
    "provider": "whatsapp",  # Filter by provider
    "client_id": "...",  # Filter by client (via meta_json)
    "limit": 200
}
```

**Update Pattern**:
```python
# For each channel:
existing = repo.get_chat_channel(db_path, channel_id)
repo.upsert_chat_channel(
    db_path,
    channel_id=channel_id,
    provider=new_provider or existing.provider,
    handle=existing.handle,
    display_name=existing.display_name,
    meta_json=new_meta or existing.meta_json,
    created_at=existing.created_at
)
```

#### 3. Clients

**Bulk Actions**:
- `bulk_update_status` - Change status for selected clients
- `bulk_update_trade` - Update trade type
- `bulk_update_geo` - Update geo_city/geo_country

**Selector Criteria**:
```python
{
    "client_ids": [...],  # Explicit list
    "status": "live",  # Filter by status
    "trade": "plumber",  # Filter by trade
    "geo_country": "AU",  # Filter by country
    "geo_city": "Sydney",  # Filter by city
    "limit": 200
}
```

**Update Pattern**:
```python
# For each client:
existing = repo.get_client(db_path, client_id)
updated = Client(
    ...existing fields...,
    status=new_status,  # or trade=new_trade, geo_city=new_city
    ...
)
repo.upsert_client(db_path, updated, apply_defaults=False)
```

#### 4. Leads

**Bulk Actions**:
- `bulk_update_status` - Change status for selected leads
- `bulk_update_booking_status` - Update booking status
- `bulk_assign_outcome` - Set outcome values

**Selector Criteria**:
```python
{
    "lead_ids": [...],  # Explicit list
    "status": "new",  # Filter by status
    "booking_status": "none",  # Filter by booking status
    "client_id": "...",  # Filter by client (via page_id -> client_id)
    "since_iso": "...",  # Filter by date
    "until_iso": "...",
    "limit": 200
}
```

**Update Pattern**:
```python
# For each lead:
repo.update_lead_outcome(
    db_path,
    lead_id=lead_id,
    status=new_status,
    booking_status=new_booking_status,
    booking_value=new_value,
    ...
)
```

## Implementation Plan

### Phase 1: Repository Functions

Add bulk update functions to repositories:

**`repo_service_packages.py`**:
```python
def bulk_update_active(
    db_path: str,
    package_ids: List[str],
    active: bool
) -> int:
    """Bulk update active status. Returns count updated."""
    
def bulk_update_price(
    db_path: str,
    package_ids: List[str],
    price: float
) -> int:
    """Bulk update price. Returns count updated."""
```

**`repo_chat_channels.py`**:
```python
def bulk_update_provider(
    db_path: str,
    channel_ids: List[str],
    provider: ChatProvider
) -> int:
    """Bulk update provider. Returns count updated."""
```

**`repo_clients.py`**:
```python
def bulk_update_status(
    db_path: str,
    client_ids: List[str],
    status: str
) -> int:
    """Bulk update client status. Returns count updated."""
```

### Phase 2: Service Layer Functions

Add bulk operation functions to `service.py`:

```python
def run_bulk_update_packages(
    db_path: str,
    selector: dict,
    updates: dict,  # {"active": True} or {"price": 1500.0}
    mode: str = "dry_run",
    notes: str = None
) -> BulkOp:
    """Bulk update service packages."""
    
def run_bulk_update_channels(
    db_path: str,
    selector: dict,
    updates: dict,  # {"provider": "whatsapp"} or {"meta_json": {...}}
    mode: str = "dry_run",
    notes: str = None
) -> BulkOp:
    """Bulk update chat channels."""
```

### Phase 3: API Endpoints

Add endpoints to console routes:

**`console_routes_service_packages.py`**:
```python
@admin_router.post("/api/service-packages/bulk-update")
def bulk_update_packages(
    payload: BulkUpdatePackagesIn,
    request: Request,
    _=Depends(_admin)
):
    """Bulk update service packages."""
```

**`console_routes_chat_channels.py`**:
```python
@admin_router.post("/api/chat/channels/bulk-update")
def bulk_update_channels(
    payload: BulkUpdateChannelsIn,
    request: Request,
    _=Depends(require_role("operator"))
):
    """Bulk update chat channels."""
```

### Phase 4: Frontend UI

Add bulk update UI to pages:

**Features**:
- Checkbox selection for entities
- "Select All" / "Select None" buttons
- Bulk action dropdown (Activate/Deactivate/Update Price/etc.)
- Bulk update form modal
- Progress indicator during bulk operation
- Results summary (success/failed counts)

## Database Schema for Bulk Operations

**Existing Table**: `bulk_ops`

```sql
CREATE TABLE IF NOT EXISTS bulk_ops (
    bulk_id TEXT PRIMARY KEY,
    mode TEXT NOT NULL,  -- 'dry_run' or 'execute'
    action TEXT NOT NULL,  -- 'validate', 'publish', 'pause', 'bulk_update_packages', etc.
    selector_json TEXT NOT NULL,  -- JSON selector criteria
    status TEXT NOT NULL,  -- 'queued', 'running', 'done', 'failed'
    result_json TEXT NOT NULL,  -- JSON results with counters
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    claimed_by TEXT,
    claimed_at TEXT
);
```

**New Actions to Support**:
- `bulk_update_packages` - Update service packages
- `bulk_update_channels` - Update chat channels
- `bulk_update_clients` - Update clients
- `bulk_update_leads` - Update leads

## Default State Summary Table

| Tab | Route | Auto-Load | Default Filters | Empty State |
|-----|-------|-----------|----------------|-------------|
| Dashboard | `/dashboard` | ✅ Yes | None | Loading spinner |
| Landing Pages | `/landing-pages` | ✅ Yes | All empty | Loading spinner |
| Service Packages | `/service-packages` | ✅ Yes | All empty | Loading spinner |
| Bot Setup | `/bot-setup` | ✅ Yes | Provider: any | Loading spinner |
| Reporting | `/reporting` | ❌ No | All empty | Empty state messages |
| Leads | `/leads` | ✅ Yes | All empty | Loading spinner |
| Events | `/events` | ⚠️ On expand | Page ID: empty | Loading spinner |
| Activity | `/activity` | ✅ Yes | None | Loading spinner |

## Next Steps

1. **Implement Repository Functions** - Add bulk update functions to repos
2. **Add Service Layer** - Create bulk operation functions in `service.py`
3. **Create API Endpoints** - Add bulk update endpoints
4. **Build Frontend UI** - Add selection checkboxes and bulk action UI
5. **Add Progress Tracking** - Show real-time progress during bulk operations
6. **Test & Document** - Test with real data and document usage
