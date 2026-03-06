# Security Hardening Roadmap

A phased plan to harden multi-tenant security, addressing findings from the recent security inspection. This roadmap complements [TENANT_ROADMAP.md](./TENANT_ROADMAP.md) and focuses on verification, auth, and isolation.

See [SECURITY.md](./SECURITY.md) for threats, mitigations, and env vars summary.

---

## Current Risk Summary

| Risk                             | Severity | Description                                                                 |
| -------------------------------- | -------- | --------------------------------------------------------------------------- |
| X-Tenant-ID spoofing             | High     | Header is user-supplied and unverified; any caller can impersonate a tenant |
| Public endpoints unauthenticated | High     | `/lead`, `/v1/service-packages`, etc. have no auth; rate limit only         |
| Batch 4 cross-tenant leaks       | Medium   | Events, alerts, chat, QR, payments return all tenant data with shared DB    |
| Anonymous operator               | Medium   | `require_auth_optional` grants operator role when no secret + no session    |
| Prod guardrails                  | Low      | AE_ENV=prod enforces AE_CONSOLE_SECRET; AE_REQUIRE_SECRET can trigger same  |

---

## Phase S1: Immediate Guardrails (Low Effort) ✅

**Goal:** Tighten production defaults without breaking dev ergonomics.

| Deliverable                                       | Notes                                                                                                    |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Disable anonymous operator in prod                | `require_auth_optional`: when `_is_prod()` True, never return anonymous operator                         |
| Document AE_ENV / AE_REQUIRE_SECRET               | TENANT_DEV.md, SECURITY.md                                                                               |
| Rate limit public endpoints more strictly in prod | AE_LEAD_RL_PER_MIN, AE_LEAD_RL_BURST with lower defaults (10/min, burst 20) when prod                    |

**Outcome:** Prod deployments cannot accidentally run with anonymous auth.

---

## Phase S2: X-Tenant-ID Verification (High Impact) ✅

**Goal:** Bind tenant identity to authentication so X-Tenant-ID cannot be spoofed by untrusted callers.

**Option A — Session-scoped tenant (Console):**  
Store `tenant_id` in session at login; validate X-Tenant-ID against it.

**Option B — API key → tenant mapping (Public / programmatic):**  
API key is issued per tenant; key lookup returns tenant_id; X-Tenant-ID must match or is overwritten.

| Item                    | Notes                                                                       |
| ----------------------- | --------------------------------------------------------------------------- |
| Session tenant_id       | Added to sessions; set at login; validate X-Tenant-ID == session.tenant_id  |
| API keys table          | `api_keys(key_hash, tenant_id, name, created_at)`                           |
| Middleware / helper     | `get_verified_tenant_id(request)` — returns tenant when bound to auth       |

**Outcome:** Tenant scope comes from authenticated identity, not from an unverified header.

---

## Phase S3: Public Endpoint Auth ✅

**Goal:** Protect public endpoints from arbitrary tenant spoofing and abuse.

| Deliverable              | Notes                                                                          |
| ------------------------ | ------------------------------------------------------------------------------ |
| Optional tenant-scoped API key | X-AE-API-KEY or Authorization: Bearer; used for /lead, /v1/service-packages, etc. |
| When key present         | Use key's tenant_id; validate X-Tenant-ID                                     |
| When key absent          | Keep current behavior (rate limit only) for backward compatibility             |
| Landing page integration | CLI: `ae auth-create-api-key --tenant-id <id>`                                 |

**Outcome:** Public API can enforce tenant-scoped keys in production while remaining open for dev/testing.

---

## Phase S4: Batch 4 Route Scoping ✅

**Goal:** Add client_id filtering to routes that currently return cross-tenant data with shared DB.

| Route Area         | Entity→Client Link                   | Approach                                      |
| ------------------ | ------------------------------------ | --------------------------------------------- |
| Events             | events → page_id → page.client_id    | Filter by client_id via page join             |
| Alerts             | Global (thresholds, notify config)   | Keep global for now                            |
| Chat channels      | meta_json.client_id                  | Add client_id filter; validate on get/update  |
| Chat conversations | conversation → lead → client_id      | Filter list by client_id                       |
| QR attributions    | attribution → menu → client_id       | Filter list by client_id                       |
| Payments           | payment → lead → client_id           | Add client_id filter to list                  |

**Outcome:** Shared DB deployment returns only scoped tenant data for Batch 4 routes.

---

## Phase S5: Operational Hardening ✅

**Goal:** Defensible posture for production and multi-tenant ops.

| Deliverable              | Notes                                                                    |
| ------------------------ | ------------------------------------------------------------------------ |
| Log tenant_id in logs    | RequestIdMiddleware includes tenant_id in JSON log when set              |
| CORS tighten in prod     | get_cors_allowlist(): `*` rejected when AE_ENV=prod; require explicit    |
| Security doc             | [SECURITY.md](./SECURITY.md)                                             |

**Outcome:** Easier auditing and incident response for multi-tenant deployments.

---

## Relationship to TENANT_ROADMAP

| TENANT_ROADMAP Phase     | Security Roadmap                                           |
| ------------------------ | ---------------------------------------------------------- |
| Phase 3: Auth & API Keys | Overlaps with S2, S3 — per-tenant keys and session scoping |
| Phase 4: Public API      | S3 strengthens with auth for public endpoints              |
| Phase 6: Observability   | S5 adds tenant-aware logging                               |

---

## Execution Order

1. **S1** — Quick wins, no schema changes
2. **S2** — Highest impact; session schema + auth flow
3. **S4** — Closes Batch 4 cross-tenant leak
4. **S3** — Public endpoint API keys
5. **S5** — Logging, CORS, SECURITY.md
