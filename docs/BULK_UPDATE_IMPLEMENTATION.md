# Bulk Update Implementation for Service Packages

## Summary

Bulk update functionality has been implemented for Service Packages, following the same pattern as existing bulk operations for Pages.

## Files Modified/Created

### 1. Repository Layer (`src/ae/repo_service_packages.py`)

**Added Functions**:
- `list_packages_filtered()` - List packages with filters for bulk operations (supports explicit package_ids)
- `bulk_update_active()` - Bulk update active status for multiple packages
- `bulk_update_price()` - Bulk update price for multiple packages  
- `bulk_delete_packages()` - Bulk delete multiple packages

**Key Features**:
- Uses SQL `IN` clause for efficient batch updates
- Returns count of affected rows
- Preserves `updated_at` timestamp

### 2. Service Layer (`src/ae/service_bulk_packages.py` - NEW FILE)

**Added Functions**:
- `_resolve_bulk_package_targets()` - Resolve selector criteria to package IDs
- `run_bulk_update_packages()` - Main bulk update function
- `run_bulk_delete_packages()` - Main bulk delete function

**Key Features**:
- Creates `BulkOp` records for tracking
- Supports dry-run mode
- Progress tracking via `BulkOp.result_json`
- Activity logging
- Handles errors gracefully (continues processing other packages)

**Update Types Supported**:
- `active`: bool - Set active status
- `price`: float - Set price
- Both can be updated in a single operation

**Selector Criteria**:
- `package_ids`: List[str] - Explicit package IDs
- `client_id`: str - Filter by client
- `active`: bool - Filter by active status
- `limit`: int - Maximum packages (default: 200)

### 3. API Layer (`src/ae/console_routes_service_packages.py`)

**Added Endpoints**:

#### `POST /api/service-packages/bulk-update`

**Request Body**:
```json
{
  "package_ids": ["pkg1", "pkg2"],  // Optional: explicit IDs
  "client_id": "client1",            // Optional: filter by client
  "active": true,                     // Optional: filter by active status
  "limit": 200,                      // Optional: max packages (default: 200)
  "mode": "dry_run",                 // "dry_run" or "execute"
  "updates": {                       // Required: update fields
    "active": true,                   // Optional: set active status
    "price": 1500.0                   // Optional: set price
  },
  "notes": "Bulk activation"        // Optional: operation notes
}
```

**Response**:
```json
{
  "ok": true,
  "bulk_id": "bulk_abc123",
  "status": "done",
  "action": "bulk_update_packages_active",
  "mode": "dry_run",
  "result": {
    "packages": [
      {
        "package_id": "pkg1",
        "status": "would_update",
        "current": {"active": false, "price": 1000.0},
        "updates": {"active": true}
      }
    ],
    "counters": {
      "total": 5,
      "updated": 0,
      "skipped": 2,
      "failed": 0
    },
    "updates": {"active": true}
  }
}
```

#### `POST /api/service-packages/bulk-delete`

**Request Body**:
```json
{
  "package_ids": ["pkg1", "pkg2"],  // Optional: explicit IDs
  "client_id": "client1",            // Optional: filter by client
  "active": false,                    // Optional: filter by active status
  "limit": 200,                      // Optional: max packages
  "mode": "dry_run",                 // "dry_run" or "execute"
  "notes": "Cleanup inactive packages"  // Optional
}
```

**Response**:
```json
{
  "ok": true,
  "bulk_id": "bulk_def456",
  "status": "done",
  "action": "bulk_delete_packages",
  "mode": "dry_run",
  "result": {
    "packages": [
      {
        "package_id": "pkg1",
        "status": "would_delete",
        "name": "Basic Package",
        "client_id": "client1"
      }
    ],
    "counters": {
      "total": 3,
      "deleted": 0,
      "skipped": 0,
      "failed": 0
    }
  }
}
```

### 4. Repository Exports (`src/ae/repo.py`)

**Added Exports**:
- `list_packages_filtered`
- `bulk_update_active`
- `bulk_update_price`
- `bulk_delete_packages`

### 5. Service Imports (`src/ae/service.py`)

**Added Import**:
```python
from .service_bulk_packages import run_bulk_update_packages, run_bulk_delete_packages
```

## Usage Examples

### Example 1: Activate All Packages for a Client (Dry Run)

```bash
curl -X POST http://localhost:8000/api/service-packages/bulk-update?db=acq.db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "client_id": "client1",
    "mode": "dry_run",
    "updates": {"active": true}
  }'
```

### Example 2: Update Price for Specific Packages

```bash
curl -X POST http://localhost:8000/api/service-packages/bulk-update?db=acq.db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "package_ids": ["pkg1", "pkg2", "pkg3"],
    "mode": "execute",
    "updates": {"price": 2000.0},
    "notes": "Price increase Q1 2026"
  }'
```

### Example 3: Delete Inactive Packages (Dry Run)

```bash
curl -X POST http://localhost:8000/api/service-packages/bulk-delete?db=acq.db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "active": false,
    "mode": "dry_run",
    "notes": "Cleanup inactive packages"
  }'
```

## Status Tracking

All bulk operations create `BulkOp` records in the database:

- **Status Values**: `queued` → `running` → `done` / `failed`
- **Progress**: Updated in real-time via `result_json`
- **Activity Log**: All operations logged to activity table

## Error Handling

- **Package Not Found**: Marked as `failed` with reason, operation continues
- **No Change Needed**: Marked as `skipped` with reason
- **Validation Errors**: Returned in response with HTTP 400
- **Database Errors**: Caught per-package, operation continues

## Testing Checklist

- [ ] Test bulk update active status (dry_run)
- [ ] Test bulk update active status (execute)
- [ ] Test bulk update price (dry_run)
- [ ] Test bulk update price (execute)
- [ ] Test bulk update both active and price
- [ ] Test bulk delete (dry_run)
- [ ] Test bulk delete (execute)
- [ ] Test with package_ids selector
- [ ] Test with client_id selector
- [ ] Test with active selector
- [ ] Test error handling (invalid package_id)
- [ ] Test activity logging
- [ ] Test BulkOp record creation
- [ ] Test progress tracking

## Next Steps

1. **Frontend UI**: Add bulk selection checkboxes and action buttons
2. **Progress Display**: Show real-time progress during bulk operations
3. **Results View**: Display bulk operation results in UI
4. **Extend to Other Entities**: Apply same pattern to Chat Channels, Clients, Leads

## Related Documentation

- `docs/DB_INTEGRATION_AND_BULK_UPDATES.md` - Design document
- `docs/TAB_DEFAULT_STATES.md` - Console tab states
