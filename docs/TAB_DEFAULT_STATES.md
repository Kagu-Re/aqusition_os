# Console Tab Default States Quick Reference

## Overview

This document provides a quick reference for the default state, auto-load behavior, and filter defaults for each console tab.

## Tab States Summary

### ✅ Auto-Loads on Page Load

| Tab | Route | Loading State | Filters Default |
|-----|-------|---------------|-----------------|
| **Dashboard** | `/dashboard` | Spinner: "Loading..." | None |
| **Landing Pages** | `/landing-pages` | Spinner: "Loading landing pages..." | All empty |
| **Service Packages** | `/service-packages` | Spinner: "Loading service packages..." | All empty |
| **Bot Setup** | `/bot-setup` | Spinner: "Loading chat channels..." | Provider: any |
| **Leads** | `/leads` | Spinner: "Loading leads..." | All empty |
| **Activity** | `/activity` | Spinner: "Loading activity..." | None |

### ⚠️ Conditional Auto-Load

| Tab | Route | Loading State | Trigger |
|-----|-------|---------------|---------|
| **Events** | `/events` | Spinner: "Loading events..." | On section expand |

### ❌ Manual Load Required

| Tab | Route | Empty State | Action Required |
|-----|-------|-------------|------------------|
| **Reporting** | `/reporting` | Multiple empty states | Click "Load Report" |

## Detailed Tab Breakdown

### 1. Dashboard (`/dashboard`)

**Auto-Load**: ✅ Yes

**Load Functions Called**:
- `loadKpis()` - KPI charts
- `loadActivity()` - Activity feed
- Summary metrics (leads, revenue, ROAS, campaigns)

**Default Filters**: None

**Empty States**:
- Activity section: Loading spinner
- Summary cards: "—" placeholders

**Data Sources**:
- `/api/stats/kpis?db=...&day_from=...&day_to=...`
- `/api/activity?db=...&limit=200`
- `/api/leads?db=...&limit=1`
- `/api/stats/roas?db=...`
- `/api/stats/campaigns?db=...`

---

### 2. Landing Pages (`/landing-pages`)

**Auto-Load**: ✅ Yes (`loadLandingPages()`)

**Default Filters**:
- `filter_client_id`: Empty
- `filter_template_id`: Empty
- `filter_status`: "any"

**Form Defaults**:
- `template_id`: "trade_lp"
- `locale`: "en-AU"
- `page_status`: "draft"

**Empty State**: 
```
<div class="empty-state">
  <div class="spinner">Loading landing pages...</div>
</div>
```

**Data Sources**:
- `/api/pages?db=...&client_id=...&template_id=...&page_status=...`

---

### 3. Service Packages (`/service-packages`)

**Auto-Load**: ✅ Yes (`loadServicePackages()`)

**Default Filters**:
- `filter_client_id`: Empty
- `filter_active`: "any"

**Form Defaults**: All empty

**Empty State**:
```
<div class="empty-state">
  <div class="spinner">Loading service packages...</div>
</div>
```

**Data Sources**:
- `/api/service-packages?db=...&client_id=...&active=...`

---

### 4. Bot Setup (`/bot-setup`)

**Auto-Load**: ✅ Yes

**Load Functions Called**:
- `loadChatChannels()` - Chat channels list
- `loadTelegramConfig()` - Telegram configuration

**Default Filters**:
- `filter_provider`: "any" (empty value)

**Empty State**:
```
<div class="empty-state">
  <div class="spinner">Loading chat channels...</div>
</div>
```

**Data Sources**:
- `/api/chat/channels?db=...&provider=...`
- `/api/notify/config?db=...`

---

### 5. Reporting (`/reporting`)

**Auto-Load**: ❌ No (manual "Load Report" click required)

**Default Filters**:
- `report_from`: Empty (no date)
- `report_to`: Empty (no date)
- `report_client_id`: Empty
- `report_page_id`: Empty
- `report_platform`: "All Platforms"

**Empty States**:
- KPI Cards: Empty (no cards shown)
- Campaign Performance: "Loading campaign data..." spinner
- Page Performance: "No page data loaded" message
- Revenue & ROAS: "No revenue data loaded" message

**Load Function**: `loadReportingData()` (manual trigger)

**Data Sources**:
- `/api/kpi/page/{page_id}?db=...&since_iso=...&platform=...`
- `/api/kpi/client/{client_id}?db=...&since_iso=...&platform=...`
- `/api/stats/campaigns?db=...&since_iso=...&until_iso=...`

---

### 6. Leads (`/leads`)

**Auto-Load**: ✅ Yes (`loadLeads()`)

**Default Filters**:
- `leads_search`: Empty
- `leads_status`: "All Status" (empty value)
- `leads_booking_status`: "All Booking Status" (empty value)
- `leads_date_from`: Empty
- `leads_date_to`: Empty

**Empty State**:
```
<div class="empty-state">
  <div class="spinner">Loading leads...</div>
</div>
```

**Data Sources**:
- `/api/leads?db=...&limit=...&status=...&booking_status=...`

---

### 7. Events (`/events`)

**Auto-Load**: ⚠️ On section expand (`loadEvents()`)

**Default Filters**:
- `events_page_id`: Empty

**Empty State**: Loading spinner (shown when section expanded)

**Data Sources**:
- `/api/events?db=...&page_id=...&limit=200`

---

### 8. Activity (`/activity`)

**Auto-Load**: ✅ Yes (`loadActivity()`)

**Default Filters**: None

**Empty State**: Loading spinner

**Data Sources**:
- `/api/activity?db=...&limit=200&action=...&entity_type=...&entity_id=...`

---

## Filter Reset Behavior

When filters are reset (via "Reset" button or programmatically):

| Tab | Reset Behavior |
|-----|----------------|
| Landing Pages | All filters → empty, form → defaults, reload data |
| Service Packages | All filters → empty, reload data |
| Bot Setup | Provider filter → "any", reload data |
| Reporting | All filters → empty, clear all data displays |
| Leads | All filters → empty, reload data |

## Loading State Patterns

### Pattern 1: Spinner with Text
```html
<div class="empty-state">
  <div class="spinner" style="margin: 0 auto;"></div>
  <div class="empty-state-title mt-4">Loading...</div>
</div>
```

### Pattern 2: Icon with Message
```html
<div class="empty-state">
  <div class="empty-state-icon" style="font-size: 64px; opacity: 0.6;">📊</div>
  <div class="empty-state-title">No data loaded</div>
  <div class="empty-state-description">Click "Load Report" to view data</div>
</div>
```

## Auto-Load Implementation Pattern

Most tabs use this pattern:

```javascript
// Auto-load on page load
(async function() {
  await new Promise(resolve => setTimeout(resolve, 100));
  if (typeof loadFunction === 'function') {
    await loadFunction();
  }
})();

// Also expose globally for manual refresh
window.loadFunction = loadFunction;
```

## Database Query Pattern

All list endpoints follow this pattern:

```
GET /api/{entity}?db={db_path}&{filter1}={value1}&{filter2}={value2}&limit={limit}
```

**Response Format**:
```json
{
  "count": 10,
  "items": [...],
  "total": 10  // Optional, for pagination
}
```

## Common Filter Types

1. **Text Input**: Client ID, Template ID, Search
2. **Dropdown**: Status, Provider, Platform
3. **Date Picker**: From/To dates
4. **Boolean**: Active/Inactive (via dropdown: any/true/false)

## Notes

- All tabs respect the `db` query parameter (defaults to "acq.db")
- Loading states are shown immediately on page load
- Empty states transition to data display after successful load
- Error states show error messages in place of empty states
- Filters are applied on "Load" button click (not real-time)
