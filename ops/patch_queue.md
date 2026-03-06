- [x] P-0010 Refactor repo module into domain files while keeping repo.py facade (v1.6.0) [2026-02-03T08:46:20Z]

- [x] OP-0022: Split Public API from Operator Console (public_api.py + router split + CLI run-public)

## P-20260207-0001 — Group API Routes by Domain (2026-02-07T17:04:55Z)
✅ done
- patch_id: `P-20260207-0001`
- client_id: `system`
- priority: **high**
- type: **refactor**
- **Deliverables:**
  - Extract alerts routes to `console_routes_alerts.py`
  - Extract stats routes to `console_routes_stats.py`
  - Extract bulk operations to `console_routes_bulk.py`
  - Create `console_routes_analytics.py` for KPI/revenue routes
  - Update `console_app.py` to import grouped routers
- **Acceptance Criteria:**
  - All routes organized by domain
  - No routes remain in `console_app.py` (except app setup)
  - All tests pass
  - Console functionality unchanged

## P-20260207-0002 — Replace Star Imports with Explicit Imports (2026-02-07T17:04:55Z)
⬜ planned
- patch_id: `P-20260207-0002`
- client_id: `system`
- priority: **high**
- type: **refactor**
- **Deliverables:**
  - Replace `from .console_support import *` with explicit imports
  - Ensure `console_support.py` has proper `__all__` definition
  - Update all files using star imports
- **Acceptance Criteria:**
  - No star imports remain
  - All imports explicit and clear
  - All tests pass
  - No functionality changes

## P-20260207-0003 — Create Frontend Component Library (2026-02-07T17:04:55Z)
⬜ planned
- patch_id: `P-20260207-0003`
- client_id: `system`
- priority: **high**
- type: **feature**
- **Deliverables:**
  - Create `shared/components/alerts.js` (alert list, card, playbook UI)
  - Create `shared/components/tables.js` (data tables, sorting, filters)
  - Create `shared/components/forms.js` (form inputs, modals, bulk actions)
  - Create `shared/components/cards.js` (KPI cards, status cards)
  - Create `shared/components/index.js` (re-exports)
  - Update existing pages to use components
- **Acceptance Criteria:**
  - Components are reusable across pages
  - Existing functionality preserved
  - Code duplication reduced
  - All tests pass

## P-20260207-0004 — Create Domain-Specific Services (2026-02-07T17:04:55Z)
⬜ planned
- patch_id: `P-20260207-0004`
- client_id: `system`
- priority: **medium**
- type: **refactor**
- **Deliverables:**
  - Create `service_operations.py` (alerts, guardrails, bulk ops)
  - Create `service_analytics.py` (KPI, reporting)
  - Create `service_content.py` (page/content logic)
  - Move business logic from routes to services
- **Acceptance Criteria:**
  - Business logic separated from HTTP handling
  - Services are testable independently
  - Routes call service layer
  - All tests pass
