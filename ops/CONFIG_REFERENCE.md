# Configuration Reference (AE_*)

This document defines the supported environment variables for portable deployments.

## Public API
### AE_PUBLIC_CORS_ORIGINS
Comma-separated list of allowed origins for CORS.

- Example: `https://example.com,https://www.example.com`
- Default: `*` (dev-friendly)

### AE_LEAD_RL_PER_MIN
Rate limiter refill rate (token bucket) for `POST /lead`.

- Default: `30`
- Set `0` to disable app-level rate limiting.

### AE_LEAD_RL_BURST
Rate limiter burst capacity.

- Default: `60`
- Set `0` to disable app-level rate limiting.

## Operator Console
### AE_CONSOLE_SECRET
Optional shared secret for admin bypass and API protection.

- If set, clients must send header: `X-AE-SECRET: <secret>`
- Default: empty (secret disabled)

## Environment / Guardrails
### AE_ENV
Environment mode.

- `prod` enables stricter guardrails (see `console_support.py`).
- Default: empty.

### AE_REQUIRE_SECRET
If set to truthy, treat as production and require `AE_CONSOLE_SECRET`.

### AE_DB_PATH (legacy)
Legacy sqlite path. Prefer `AE_DB_URL`.
Console/auth DB path (sqlite) used by the operator console session store.

**Note:** this project currently supports SQLite paths and dev DB overrides. A future patch will unify DB config via `AE_DB_URL`.

## Database
### AE_DB_URL
Primary database locator. Today supports sqlite URLs; Postgres will be added later.

- Example: `postgresql://user:pass@host:5432/db`


## Observability
### AE_LOG_REQUESTS
Enable request logging middleware (JSON lines to stdout).

- Default: `1` (enabled)

### AE_HEALTH_SHOW_DB_PATH
Include resolved sqlite file path in `/health` and `/ready` responses.

- Default: `0` in production (`AE_ENV=prod`), otherwise path is shown.


## Docker Compose convention
When using the included `docker-compose.yml`, a named volume is mounted at `/data` and the default DB is:

- `AE_DB_URL=sqlite:////data/acq.db`
