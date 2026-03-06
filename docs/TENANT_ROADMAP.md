# Multi-Tenant Development Roadmap

Phased plan for multi-tenant infrastructure on the Acquisition Engine.

---

## Phase 1: Foundation ✅ (Done)

**Goal:** Tenant resolution + request-scoped tenant_id, DB-per-tenant wiring.

| Deliverable | Status |
|-------------|--------|
| `src/ae/tenant/` (config, middleware, context) | ✅ |
| `AE_MULTI_TENANT_ENABLED` feature flag | ✅ |
| Tenant resolution (header, subdomain, path) | ✅ |
| `request.state.tenant_id` for downstream use | ✅ |
| `resolve_db_path(tenant_id=...)` for DB-per-tenant | ✅ |
| `_resolve_db_for_request`, `_get_resolved_db` in console_support | ✅ |
| Middleware wired in local_dev_server | ✅ |
| `docs/TENANT_DEV.md` | ✅ |

---

## Phase 2: Route Migration & Shared-DB Enforcement ✅ (Done)

**Goal:** Migrate console routes to tenant-aware DB resolution; enforce tenant_id as client_id when shared DB.

| Deliverable | Status |
|-------------|--------|
| Audit routes calling `_resolve_db` / `_resolve_db_path` | ✅ |
| Migrate high-value routes to `_resolve_db_path(_, request)` | ✅ Clients, pages, leads, service_packages, menus, spend, stats, analytics, booking_requests, payment_intents, onboarding |
| `get_scoped_client_id(request)` in tenant/context | ✅ |
| Ensure no cross-tenant data access in migrated routes | ✅ client_id checks on get/update/list |
| Batch 4: events, alerts, chat, qr, retries, payments (db path only) | ✅ |
| Integration tests `tests/test_tenant_integration.py` | ✅ clients, leads, packages, menus, spend, public packages |

**Outcome:** Console usable per-tenant when multi-tenant enabled (shared DB default).

---

## Phase 3: Auth & API Keys

**Goal:** Per-tenant auth; move beyond single AE_CONSOLE_SECRET.

| Deliverable | Notes |
|-------------|-------|
| Per-tenant API keys table / config | Key → tenant_id mapping |
| Optional JWT with `client_id` / `tenant_id` claims | For public API auth |
| Session scoping: tenant_id in sessions or session→tenant mapping | Console login |
| Deprecate or keep AE_CONSOLE_SECRET as super-admin bypass | Document clearly |

**Outcome:** API consumers can auth with tenant-scoped keys; console sessions respect tenant.

---

## Phase 4: Public API & Webhooks ✅ (Partial)

**Goal:** Public API, Telegram webhook, lead intake respect tenant.

| Deliverable | Status |
|-------------|--------|
| Public lead intake: resolve tenant from header/path | ✅ X-Tenant-ID as client_id |
| Public service-packages: `_resolve_db_path(_, request)`; X-Tenant-ID as client_id when not in query | ✅ |
| Public events, chat, qr: `_resolve_db_path(_, request)` for tenant-aware db | ✅ |
| Telegram webhook: tenant from bot token or config | Deferred |

**Outcome:** Public traffic correctly scoped by tenant where migrated.

---

## Phase 5: Background & Polling

**Goal:** Telegram polling, exports, cron jobs tenant-aware.

| Deliverable | Notes |
|-------------|-------|
| Telegram polling: per-tenant or tenant-scoped DB | Today: single db_path at startup |
| Export jobs, scheduled tasks: tenant_id from job config | Not request-scoped |
| Any long-running workers: tenant context from queue/job | Document pattern |

**Outcome:** Background work respects tenant boundaries.

---

## Phase 6: Operational & Observability

**Goal:** Tenant in logs, metrics, health checks.

| Deliverable | Notes |
|-------------|-------|
| Log tenant_id where available | Structured logging |
| Metrics with tenant label (optional) | Per-tenant usage, errors |
| Health check: tenant DB existence when DB-per-tenant | /health can accept ?tenant_id |
| Tenant provisioning / bootstrap script | Create tenant DB, migrate schema |

**Outcome:** Debugging and ops work across tenants.

---

## Decisions (Locked)

| Topic | Decision |
|-------|----------|
| **DB strategy** | **Shared DB + client_id** — single DB, scope by client_id; easier to maintain and monitor |
| **Tenant identity** | **tenant_id = client_id** — no separate tenant entity; tenant_id maps directly to clients.client_id |
| **Auth model** | Shared users with tenant role/scope (Phase 3) |
| **Subdomain routing** | Path + header for dev; subdomain when DNS ready |

---

## Branch & Release

- Branch: `feature/tenant-*` or long-lived `tenant`
- Rebase on `main` weekly
- Release: keep `AE_MULTI_TENANT_ENABLED=0` default until Phase 2+ is stable

---

## References

- [TENANT_DEV.md](./TENANT_DEV.md) — touch points, env vars, migration path
- [SECURITY_HARDENING_ROADMAP.md](./SECURITY_HARDENING_ROADMAP.md) — phased security hardening plan
- [SECURITY.md](./SECURITY.md) — threats, mitigations, env vars
- Guidelines: tenant logic in `src/ae/tenant/`; avoid changing product features (Money Board, booking, Telegram flows)
