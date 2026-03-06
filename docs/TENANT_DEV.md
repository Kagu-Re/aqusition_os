# Multi-Tenant Development Guide

Multi-tenant infrastructure for the Acquisition Engine. Tenant resolution is gated by `AE_MULTI_TENANT_ENABLED=1` (default off). When disabled, single-tenant behavior is preserved.

**Roadmap:** See [TENANT_ROADMAP.md](./TENANT_ROADMAP.md) for phased development plan. **Security:** See [SECURITY_HARDENING_ROADMAP.md](./SECURITY_HARDENING_ROADMAP.md) and [SECURITY.md](./SECURITY.md).

## Production Guardrails

| Env Var | Description |
|---------|-------------|
| `AE_ENV` | Set to `prod` or `production` to enable production guardrails. |
| `AE_REQUIRE_SECRET` | Set to `1`, `true`, `yes`, or `y` to require secrets even when `AE_ENV` is not prod. |

When **AE_ENV=prod** or **AE_REQUIRE_SECRET=1**:
- **AE_CONSOLE_SECRET** must be set; startup fails otherwise.
- **AE_DB_PATH** or **AE_DB_URL** must be set; startup fails otherwise.
- Anonymous operator is disabled; `require_auth_optional` requires a valid session or X-AE-SECRET.
- Public endpoint rate limits use stricter defaults (10/min, burst 20) unless overridden by `AE_LEAD_RL_PER_MIN` and `AE_LEAD_RL_BURST`.

## Feature Flag

| Env Var | Default | Description |
|---------|---------|-------------|
| `AE_MULTI_TENANT_ENABLED` | 0 / off | Enable tenant resolution middleware and tenant-aware scoping. |
| `AE_TENANT_DB_PER_TENANT` | off | Optional: separate DB per tenant. **Default: shared DB**, tenant_id = client_id for scoping. |
| `AE_TENANT_DB_DIR` | data | Base directory for tenant DBs when DB-per-tenant. |

## Tenant Resolution Order

1. **X-Tenant-ID header** — explicit; highest precedence
2. **Subdomain** — e.g. `tenant1.example.com` (skips `www`, `localhost`, `api`)
3. **Path prefix** — e.g. `/t/tenant1/...`

Sets `request.state.tenant_id` for downstream use.

## Touch Points

### `src/ae/tenant/`

- `config.py` — `is_multi_tenant_enabled()`, `get_tenant_db_dir()`
- `middleware.py` — `TenantResolutionMiddleware` (resolves tenant, sets `request.state.tenant_id`)
- `context.py` — `get_tenant_id_from_request(request)`, `get_scoped_client_id(request)` — returns tenant_id when multi-tenant, None otherwise

### `src/ae/local_dev_server.py`

- `TenantResolutionMiddleware` added when `AE_MULTI_TENANT_ENABLED=1`
- Middleware order: `RequestIdMiddleware` → `TenantResolutionMiddleware` (if enabled) → `AbuseControlsMiddleware`

### `src/ae/console_support.py`

- `_resolve_db(db_param)` — legacy; no tenant (used by `Depends(_resolve_db)`)
- `_resolve_db_for_request(request, db_param)` — uses tenant path only when `AE_TENANT_DB_PER_TENANT`; shared DB uses `db_param` unchanged
- `_resolve_db_path(db_path, request=None)` — alias; pass `request` for tenant-aware
- `_get_resolved_db(request, db_param)` — dependency-friendly; use `Depends(_get_resolved_db)` for tenant-aware routes

### `src/ae/storage.py`

- `resolve_db_path(..., tenant_id=None)` — when `tenant_id` + `AE_TENANT_DB_PER_TENANT`, returns `{AE_TENANT_DB_DIR}/acq_{tenant_id}.db`

### `src/ae/auth.py`

- **Future**: per-tenant API keys, JWT with `client_id`. Today: single `AE_CONSOLE_SECRET`, shared users/sessions.

### Migrated Routes (Phase 2 + 4)

- **Batch 1:** `console_routes_service_packages.py`, `console_routes_menus.py` — full scoping
- **Batch 2:** `console_routes_spend.py`, `console_routes_stats.py`, `console_routes_analytics.py` — scoped stats/kpi
- **Batch 3:** `console_routes_booking_requests.py`, `console_routes_payment_intents.py`, `console_routes_onboarding.py` — scoped via package/lead
- **Batch 4:** `console_routes_events.py`, `console_routes_alerts.py`, chat channels/conversations/templates/automations, qr, retries, payments — `_resolve_db_path` only
- **Phase 4 public:** `console_routes_service_packages_public.py`, events_public, chat_public, qr_public — tenant-aware

### Files Not Touched (per guidelines)

- `console_routes_money_board.py`, `service_booking.py`, `telegram_polling.py` — product features
- `repo_*` — client_id filtering added where needed (list_booking_requests, list_payment_intents, kpi_stats, campaign_stats, revenue_stats, roas_stats); tenant enforcement in app layer

## Migration Path for Routes

To use tenant-aware DB resolution, pass `request` to `_resolve_db_path` or use the dependency:

```python
# Option 1: pass request
db_path = _resolve_db_path(request.query_params.get("db"), request)

# Option 2: use dependency
@router.get("/...")
def handler(db_path: str = Depends(_get_resolved_db)):
    ...
```

## Branch

Work on `feature/tenant-*` or long-lived tenant branch. Rebase on main weekly.
