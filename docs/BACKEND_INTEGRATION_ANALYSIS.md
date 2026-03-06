# Backend Integration Analysis

This document analyzes the backend integration for the newly created frontend pages.

## Summary

**Status**: ⚠️ **Partial Integration** - Some endpoints are missing and need to be implemented.

## Endpoint Analysis

### ✅ Landing Pages (`landing-pages.html`)

#### Existing Endpoints
- ✅ `GET /api/pages` - List pages (with filters)
- ✅ `GET /api/pages/{page_id}` - Get single page
- ✅ `POST /api/pages/{page_id}/validate` - Validate page
- ✅ `POST /api/pages/{page_id}/publish` - Publish page

#### Missing Endpoints
- ❌ `POST /api/pages` - **CREATE PAGE ENDPOINT MISSING**
  - Frontend calls: `POST /api/pages` with payload
  - Need to implement page creation endpoint

#### Frontend Calls
```javascript
// Create page
POST /api/pages?db=acq.db
Body: {
  page_id, client_id, template_id, template_version,
  page_slug, page_url, page_status, locale, service_focus, content_version
}

// List pages
GET /api/pages?db=acq.db&client_id=...&template_id=...&page_status=...

// Validate
POST /api/pages/{page_id}/validate?db=acq.db

// Publish
POST /api/pages/{page_id}/publish?db=acq.db
```

---

### ✅ Service Packages (`service-packages.html`)

#### Existing Endpoints
- ✅ `GET /api/service-packages` - List packages (with filters)
- ✅ `GET /api/service-packages/{package_id}` - Get single package
- ✅ `POST /api/service-packages` - Create package
- ✅ `PUT /api/service-packages/{package_id}` - Update package

#### Missing Endpoints
- ❌ `DELETE /api/service-packages/{package_id}` - **DELETE ENDPOINT MISSING**
  - Frontend calls: `DELETE /api/service-packages/{package_id}`
  - Need to implement delete functionality

#### Frontend Calls
```javascript
// Create package
POST /api/service-packages?db=acq.db
Body: { package_id, client_id, name, price, duration_min, addons, active, meta_json }

// List packages
GET /api/service-packages?db=acq.db&client_id=...&active=...

// Get package
GET /api/service-packages/{package_id}?db=acq.db

// Update package
PUT /api/service-packages/{package_id}?db=acq.db
Body: { name?, price?, duration_min?, addons?, active?, meta_json? }

// Delete package (MISSING)
DELETE /api/service-packages/{package_id}?db=acq.db
```

---

### ⚠️ Bot Setup (`bot-setup.html`)

#### Existing Endpoints
- ✅ `GET /api/chat/channels` - List channels
- ✅ `GET /api/chat/channels/{channel_id}` - Get single channel
- ✅ `POST /api/chat/channels` - Create/upsert channel
- ✅ `GET /api/notify/config` - Get Telegram config
- ✅ `PUT /api/notify/config` - Update Telegram config

#### Missing Endpoints
- ❌ `PUT /api/chat/channels/{channel_id}` - **UPDATE ENDPOINT MISSING**
  - Frontend calls: `PUT /api/chat/channels/{channel_id}`
  - Currently only POST (upsert) exists, but frontend expects PUT for updates
- ❌ `DELETE /api/chat/channels/{channel_id}` - **DELETE ENDPOINT MISSING**
  - Frontend calls: `DELETE /api/chat/channels/{channel_id}`

#### Frontend Calls
```javascript
// Create channel
POST /api/chat/channels?db=acq.db
Body: { channel_id, provider, handle, display_name, meta_json }

// List channels
GET /api/chat/channels?db=acq.db&provider=...

// Get channel
GET /api/chat/channels/{channel_id}?db=acq.db

// Update channel (MISSING - currently uses POST upsert)
PUT /api/chat/channels/{channel_id}?db=acq.db
Body: { provider?, handle?, display_name?, meta_json? }

// Delete channel (MISSING)
DELETE /api/chat/channels/{channel_id}?db=acq.db

// Telegram config
GET /api/notify/config?db=acq.db
PUT /api/notify/config?db=acq.db
Body: { telegram_bot_token, telegram_chat_id }
```

---

### ⚠️ Reporting (`reporting.html`)

#### Existing Endpoints
- ✅ `GET /api/stats/campaigns` - Campaign stats
- ✅ `GET /api/stats/kpis` - Overall KPIs
- ✅ `GET /api/stats/roas` - ROAS stats
- ✅ `GET /api/stats/revenue` - Revenue stats

#### Missing Endpoints
- ❌ `GET /api/kpi/page/{page_id}` - **PAGE KPI ENDPOINT MISSING**
  - Frontend calls: `GET /api/kpi/page/{page_id}?db=...&since_iso=...`
  - Need to implement page-specific KPI endpoint
- ❌ `GET /api/kpi/client/{client_id}` - **CLIENT KPI ENDPOINT MISSING**
  - Frontend calls: `GET /api/kpi/client/{client_id}?db=...&since_iso=...`
  - Need to implement client-specific KPI endpoint

#### Frontend Calls
```javascript
// Page KPIs (MISSING)
GET /api/kpi/page/{page_id}?db=acq.db&since_iso=...&until_iso=...&platform=...

// Client KPIs (MISSING)
GET /api/kpi/client/{client_id}?db=acq.db&since_iso=...&until_iso=...&platform=...

// Campaign stats (EXISTS)
GET /api/stats/campaigns?db=acq.db&sort_by=roas&min_spend=0&day_from=...&day_to=...

// Pages list (EXISTS)
GET /api/pages?db=acq.db&client_id=...&page_status=...
```

---

## Required Backend Changes

### 1. Add Page Creation Endpoint

**File**: `src/ae/console_routes_pages.py`

**Note**: `repo.upsert_page()` exists and can be used.

```python
from pydantic import BaseModel, Field
from typing import Optional

class PageCreateIn(BaseModel):
    page_id: str = Field(min_length=1)
    client_id: str = Field(min_length=1)
    template_id: str = Field(min_length=1)
    template_version: str = Field(default="1.0.0")
    page_slug: str = Field(min_length=1)
    page_url: str = Field(min_length=1)
    page_status: str = Field(default="draft")
    content_version: int = Field(default=1)
    service_focus: Optional[str] = None
    locale: str = Field(default="en-AU")

@router.post("/api/pages")
def create_page(
    payload: PageCreateIn,
    db: str,
    _: None = Depends(require_role("editor")),
):
    """Create a new landing page."""
    db_path = _resolve_db_path(db)
    from .models import Page, PageStatus
    
    page = Page(
        page_id=payload.page_id,
        client_id=payload.client_id,
        template_id=payload.template_id,
        template_version=payload.template_version,
        page_slug=payload.page_slug,
        page_url=payload.page_url,
        page_status=PageStatus(payload.page_status),
        content_version=payload.content_version,
        service_focus=payload.service_focus,
        locale=payload.locale,
    )
    
    repo.upsert_page(db_path, page)
    created = repo.get_page(db_path, page.page_id)
    return created.model_dump()
```

### 2. Add Service Package Delete Function & Endpoint

**File 1**: `src/ae/repo_service_packages.py` - Add delete function:

```python
def delete_package(db_path: str, package_id: str) -> None:
    """Delete a service package."""
    db.init_db(db_path)
    con = db.connect(db_path)
    try:
        con.execute("DELETE FROM service_packages WHERE package_id=?", (package_id,))
        con.commit()
    finally:
        con.close()
```

**File 2**: `src/ae/console_routes_service_packages.py` - Add endpoint:

```python
@admin_router.delete("/{package_id}")
def delete_service_package(
    package_id: str,
    request: Request,
    _=Depends(_admin),
):
    """Delete a service package."""
    db_path = _resolve_db(request.query_params.get("db"))
    existing = repo.get_package(db_path, package_id)
    if not existing:
        raise HTTPException(status_code=404, detail="package_not_found")
    
    repo.delete_package(db_path, package_id)
    return {"ok": True, "package_id": package_id}
```

**Also update**: `src/ae/repo.py` to export `delete_package`:
```python
from .repo_service_packages import create_package, get_package, list_packages, update_package, delete_package
```

### 3. Add Chat Channel Delete Function & Update/Delete Endpoints

**File 1**: `src/ae/repo_chat_channels.py` - Add delete function:

```python
def delete_chat_channel(db_path: str, channel_id: str) -> None:
    """Delete a chat channel."""
    con = db.connect(db_path)
    try:
        con.execute("DELETE FROM chat_channels WHERE channel_id=?", (channel_id,))
        con.commit()
    finally:
        con.close()
```

**File 2**: `src/ae/console_routes_chat_channels.py` - Add endpoints:

```python
class ChatChannelUpdateIn(BaseModel):
    provider: Optional[ChatProvider] = None
    handle: Optional[str] = Field(default=None, min_length=1)
    display_name: Optional[str] = None
    meta_json: Optional[Dict[str, Any]] = None

@admin_router.put("/api/chat/channels/{channel_id}")
def update_channel(
    channel_id: str,
    payload: ChatChannelUpdateIn,
    request: Request,
    _=Depends(require_role("operator")),
):
    """Update an existing chat channel."""
    db_path = _resolve_db(request.query_params.get("db"))
    existing = repo.get_chat_channel(db_path, channel_id)
    if not existing:
        raise HTTPException(status_code=404, detail="channel_not_found")
    
    ch = repo.upsert_chat_channel(
        db_path,
        channel_id=channel_id,
        provider=payload.provider if payload.provider else existing.provider,
        handle=payload.handle if payload.handle else existing.handle,
        display_name=payload.display_name if payload.display_name is not None else existing.display_name,
        meta_json=payload.meta_json if payload.meta_json else existing.meta_json,
        created_at=existing.created_at,  # Preserve original created_at
    )
    audit_event("chat_channel_update", request, meta={"entity_type": "chat_channel", "entity_id": channel_id})
    return ch

@admin_router.delete("/api/chat/channels/{channel_id}")
def delete_channel(
    channel_id: str,
    request: Request,
    _=Depends(require_role("operator")),
):
    """Delete a chat channel."""
    db_path = _resolve_db(request.query_params.get("db"))
    existing = repo.get_chat_channel(db_path, channel_id)
    if not existing:
        raise HTTPException(status_code=404, detail="channel_not_found")
    
    repo.delete_chat_channel(db_path, channel_id)
    audit_event("chat_channel_delete", request, meta={"entity_type": "chat_channel", "entity_id": channel_id})
    return {"ok": True, "channel_id": channel_id}
```

**Also update**: `src/ae/repo.py` to export `delete_chat_channel`:
```python
from .repo_chat_channels import (
    upsert_chat_channel, get_chat_channel, list_chat_channels, delete_chat_channel,
)
```

### 4. Add KPI Report Endpoints

**File**: `src/ae/console_routes_pages.py` or new file `src/ae/console_routes_kpi.py`

```python
@router.get("/api/kpi/page/{page_id}")
def kpi_report_page(
    page_id: str,
    db: str,
    since_iso: Optional[str] = None,
    until_iso: Optional[str] = None,
    platform: Optional[str] = None,
    _: None = Depends(require_role("viewer")),
):
    """Get KPI report for a specific page."""
    db_path = _resolve_db_path(db)
    from . import service
    
    result = service.kpi_report(
        db_path,
        page_id=page_id,
        since_iso=since_iso,
        platform=platform,
    )
    return result

@router.get("/api/kpi/client/{client_id}")
def kpi_report_client(
    client_id: str,
    db: str,
    since_iso: Optional[str] = None,
    until_iso: Optional[str] = None,
    platform: Optional[str] = None,
    _: None = Depends(require_role("viewer")),
):
    """Get KPI report for a client (aggregated across pages)."""
    db_path = _resolve_db_path(db)
    from . import reporting
    
    result = reporting.kpi_report_for_client(
        db_path,
        client_id=client_id,
        platform=platform,
        since_iso=since_iso,
    )
    return result
```

---

## Repository Functions Status

Verified repository functions:

1. ✅ `repo.upsert_page()` - **EXISTS** (can be used for create via POST endpoint)
2. ❌ `repo.delete_package()` - **MISSING** - Needs implementation in `repo_service_packages.py`
3. ❌ `repo.delete_chat_channel()` - **MISSING** - Needs implementation in `repo_chat_channels.py`
4. ✅ `repo.create_package()` - **EXISTS**
5. ✅ `repo.update_package()` - **EXISTS**
6. ✅ `repo.upsert_chat_channel()` - **EXISTS** (can be used for updates)
7. ✅ `service.kpi_report()` - **EXISTS**
8. ✅ `reporting.kpi_report_for_client()` - **EXISTS**

---

## Testing Checklist

After implementing missing endpoints:

- [ ] Test page creation via POST /api/pages
- [ ] Test service package deletion via DELETE /api/service-packages/{id}
- [ ] Test chat channel update via PUT /api/chat/channels/{id}
- [ ] Test chat channel deletion via DELETE /api/chat/channels/{id}
- [ ] Test page KPI report via GET /api/kpi/page/{id}
- [ ] Test client KPI report via GET /api/kpi/client/{id}
- [ ] Verify all endpoints return proper error codes (404, 400, etc.)
- [ ] Verify authentication/authorization on all endpoints
- [ ] Test with various filter combinations

---

## Notes

1. **Database Parameter**: All endpoints use `db` query parameter (not `db_path`)
2. **Authentication**: Most endpoints require `require_role("operator")` or `require_role("editor")`
3. **Error Handling**: Frontend expects proper HTTP status codes and error messages
4. **Response Format**: Most endpoints return JSON with `model_dump()` or similar
