## v5.7.0 — OP-PAY-001C Payment Event Hooks
- Emitted op-events from payment lifecycle: created, status_changed, and state-driving status topics (authorized/captured*/failed*/cancelled*/refunded).
- Added timeline mapping for payment topics.
- Added tests for created + authorized→captured + direct capture flows.

- 2026-02-03T08:46:20Z | v1.6.0 | Refactor: split repo.py into domain modules (repo_clients/pages/logs/work/events/bulk/stats/activity/abuse/leads/alerts). Tests pass.

## OP-0022 (v2.1.0) — Public API boundary
- Split lead intake routes into `public_router` (POST /lead) and `admin_router` (operator endpoints).
- Added `ae.public_api:app` with minimal CORS to deploy the Public API independently.
- Kept `/lead` mounted in Operator Console for backwards compatibility + tests.
- Added CLI: `ae run-public` (defaults to 127.0.0.1:8001).
