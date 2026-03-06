# Security

Summary of threats, mitigations, and environment variables for Acquisition Engine deployments.

See also [SECURITY_HARDENING_ROADMAP.md](./SECURITY_HARDENING_ROADMAP.md) for the phased implementation plan.

## Threats and Mitigations

| Threat | Severity | Mitigation |
|--------|----------|------------|
| X-Tenant-ID spoofing | High | Session-scoped tenant (login stores tenant_id); API key binds tenant; X-AE-SECRET trusted only when configured |
| Public endpoints unauthenticated | High | Optional X-AE-API-KEY or Bearer token; rate limiting; stricter limits in prod |
| Cross-tenant data leaks | Medium | client_id filtering on Batch 4 routes (events, chat, QR, payments) |
| Anonymous operator | Medium | Disabled in prod; require session or X-AE-SECRET |
| Production guardrails | Low | AE_ENV=prod enforces AE_CONSOLE_SECRET, AE_DB_PATH |

## Environment Variables

### Production Guardrails

| Var | Description |
|-----|-------------|
| `AE_ENV` | Set to `prod` or `production` for production guardrails |
| `AE_REQUIRE_SECRET` | Set to `1` to require secrets even when AE_ENV is not prod |
| `AE_CONSOLE_SECRET` | Required when AE_ENV=prod; startup fails if unset |
| `AE_DB_PATH` / `AE_DB_URL` | Required when AE_ENV=prod |

### Authentication

| Var | Description |
|-----|-------------|
| `AE_CONSOLE_SECRET` | Shared secret for admin bypass (X-AE-SECRET header) |

### Multi-Tenant

| Var | Description |
|-----|-------------|
| `AE_MULTI_TENANT_ENABLED` | Enable tenant resolution and scoping |
| `AE_TENANT_DB_PER_TENANT` | Separate DB per tenant |
| `AE_TENANT_DB_DIR` | Base directory for tenant DBs |

### Public API

| Var | Description |
|-----|-------------|
| `AE_PUBLIC_CORS_ORIGINS` | Comma-separated origins; in prod `*` is rejected |
| `AE_LEAD_RL_PER_MIN` | Rate limit refill per minute (default 30; prod default 10) |
| `AE_LEAD_RL_BURST` | Rate limit burst (default 60; prod default 20) |
| `AE_REQUIRE_API_KEY_PUBLIC` | When `1` and AE_ENV=prod, public endpoints require X-AE-API-KEY or Bearer token |

### Operational

| Var | Description |
|-----|-------------|
| `AE_LOG_REQUESTS` | Enable request logging (default 1) |

## API Keys

Create tenant-scoped API keys for public endpoints:

```bash
ae auth-create-api-key --tenant-id <client_id> --name default
```

Use via header `X-AE-API-KEY: <key>` or `Authorization: Bearer <key>`.

When `AE_REQUIRE_API_KEY_PUBLIC=1` and `AE_ENV=prod`, public endpoints (`/lead`, `/v1/service-packages`, `/v1/event`, etc.) require a valid API key; requests without one return 401.
