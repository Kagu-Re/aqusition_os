# Assumption Ledger

Updated: 2026-02-03

| Assumption ID | Assumption | Why it matters | Validation / Signal | Status |
|---|---|---|---|---|
| A-0001 | Console will run behind HTTPS in production | Cookie Secure should be enabled | Deploy config + domain TLS | 🟡 |
| A-0002 | Single-tenant ops is sufficient for MVP | Simplifies auth + data model | Client usage pattern | 🟡 |
| A-0003 | Tailwind static export is the default surface | Non-technical handoff | Operator adoption | ✅ |
| A-0004 | SQLite is sufficient for early-stage ops | Low ops overhead | Lock rate under load | 🟡 |
| A-0005 | Rate limiting is enough to deter basic abuse | Prevents budget blowups | Logs + anomalies | 🟡 |

| A-0006 | Console is not embedded cross-site | Enables SameSite/CSRF model | Headers + CSP frame-ancestors | 🟡 |

### A-0012 — Star-import compatibility
**Assumption:** Keeping `from .console_support import *` is acceptable short-term, but should be replaced with explicit imports later.
**Risk:** `__all__` may export more than intended and hide dead-code or import cycles.
**Mitigation:** Track cleanup under OP-0018 and remove star-import before public release.

### A-0013 — Stats routes grouped with spend (temporary)
**Assumption:** `/api/stats/kpi` and `/api/stats/campaign` are close enough to spend to live in `console_routes_spend.py` for now.
**Risk:** Router boundaries become fuzzy if stats expands.
**Mitigation:** If stats grows, extract to `console_routes_stats.py` and keep spend purely CRUD.

### A-0014 — Clients router keeps legacy 'secret' gate
**Assumption:** `/api/clients*` stays on `require_secret` rather than role-based sessions.
**Risk:** Two auth systems coexist (cookie/sessions vs shared secret) and can confuse ops.
**Mitigation:** Either (1) migrate clients endpoints to role-based auth, or (2) isolate secret-gated admin APIs under `/admin/*` with explicit docs.

### A-0015 — Public /lead remains mounted on the console app (temporary)
**Assumption:** It's acceptable for `/lead` to be served by the same FastAPI app that serves the Operator Console.
**Risk:** Deployment topology might want public API on a separate host / WAF / rate-limit tier.
**Mitigation:** Introduce `public_api.py` (separate app) and deploy behind a stricter edge policy; keep console behind auth.

### A-0016 — Public rate limiting is in-memory (single-process)
**Assumption:** Initial deployments use a single process, or edge limiting provides primary protection.
**Risk:** Multi-worker deployments won't share buckets; limits become per-worker.
**Mitigation:** Move limiter to Redis (or rely on Nginx/Cloudflare rate limiting) when scaling.

### A-0017 — Edge enforcement is primary protection for public endpoints
**Assumption:** Production deployments apply edge/WAF rate limiting and payload constraints for `/lead`.
**Risk:** If edge controls are missing, a bot can overwhelm the app or poison lead quality.
**Mitigation:** Keep edge config in infra repo; add a deploy checklist gate before going live.

### A-0019 — Docker is the portability baseline
**Assumption:** Container packaging is the default distribution format, even if deployment is not Docker-based (e.g., Akash, PaaS).
**Risk:** If runtime requires OS-specific deps, portability degrades.
**Mitigation:** Keep Docker image minimal and document any native deps explicitly.

### A-0020 — Settings contract is the source of truth for deploy-time config
**Assumption:** Deployments set configuration via `AE_*` env vars and avoid editing code for environment differences.
**Risk:** Hidden env usage in legacy modules can drift from the contract.
**Mitigation:** Gradually migrate remaining `os.getenv("AE_*")` reads into `Settings` (OP-0028+).

### A-0021 — SQLite remains the default store until Postgres adapter is implemented
**Assumption:** Most deployments run single-process SQLite (WAL) and accept its constraints.
**Risk:** Multi-worker deployments can cause lock contention, and backup/restore needs discipline.
**Mitigation:** Use edge rate limits; keep a single worker for console; implement Postgres adapter in a future patch without changing repo call sites.

### A-0022 — Health endpoints are non-sensitive and safe to expose publicly
**Assumption:** `/health` and `/ready` expose only minimal metadata (version, uptime, coarse DB status).
**Risk:** Path leakage could help attackers.
**Mitigation:** Keep payload minimal; avoid secrets; consider hiding `db.path` in prod if needed.

### A-0023 — Request logs are non-sensitive and avoid PII by design
**Assumption:** Request logs include only method/path/status/latency and do not include lead bodies, emails, or full IPs.
**Risk:** Developers may add extra logging in handlers.
**Mitigation:** Keep middleware log schema fixed; document “no PII in logs” as a rule; consider lint/CI check later.

### A-0024 — Single shared SQLite volume is sufficient for early deployments
**Assumption:** Console + Public can safely share a single SQLite file on a docker volume with low write contention.
**Risk:** Higher concurrency can introduce lock contention and latency spikes.
**Mitigation:** Keep one worker per service; prefer WAL mode; move to Postgres adapter when traffic requires it.

### A-0025 — Release clarity beats automation at this stage
**Assumption:** A human-readable changelog + checklist reduces drift more than heavy release automation.
**Risk:** Manual steps get skipped under time pressure.
**Mitigation:** Keep checklist short; add CI gates later (e.g., “version surfaces must match”).

### A-0026 — CI gates are the right “automation boundary” for now
**Assumption:** Enforcing invariants in CI (SSOT + changelog completeness) prevents most drift without adding heavy release machinery.
**Risk:** Contributors might bypass CI checks or disable the workflow.
**Mitigation:** Keep workflow minimal; require status checks in repo settings when hosted.

### A-0026 — CI gates prevent the most common drift
**Assumption:** The top causes of release confusion are version drift and missing changelog/log entries.
**Risk:** Team bypasses CI locally.
**Mitigation:** Put gates in CI; keep them fast; document how to run them locally.

### A-0027 — Explicit skip reason is acceptable for artifact enforcement
**Assumption:** Requiring either an artifact file or a documented skip reason prevents “silent missing deliverables”.
**Risk:** People always set `mode=skip` and ignore artifacts.
**Mitigation:** Add policy later: production releases must be `mode=file` (enforced via repo rules).

### A-0028 — Edge proxy is the safest default for public exposure
**Assumption:** Exposing only the proxy (80/443) reduces attack surface vs publishing service ports.
**Risk:** Misconfigured proxy can hide real errors or break websockets/headers.
**Mitigation:** Provide standard headers + routes; keep `/healthz`; document needed forwarded headers.

### A-0029 — Prod must ship artifacts
**Assumption:** Production releases should always include an artifact (or CI should fail).
**Risk:** Some environments use registry builds, not committed zips.
**Mitigation:** In those cases treat the “artifact” as a build output reference (future: allow `mode=registry`).

### A-0030 — Named volume backup is sufficient for early deployments
**Assumption:** Backing up `ae_data` is enough to recover the system state.
**Risk:** If additional state is introduced (e.g., external DB, object storage), backup scope must expand.
**Mitigation:** Treat backup scope as an explicit inventory; extend policy per deployment mode.

### A-0031 — Basic metrics + logs are enough for MVP ops
**Assumption:** Request count + latency + request IDs cover 80% of early incidents.
**Risk:** Silent failures or async errors not captured.
**Mitigation:** Add error-rate metrics and tracing later.

### A-0031 — Minimal metrics are enough for early-stage operations
**Assumption:** In-memory counters + request logs cover initial debugging and confidence-building.
**Risk:** Metrics reset on restart; no historical trends.
**Mitigation:** Add external metrics backend when real traffic starts (Prometheus/OTel).

### A-0032 — PII redaction heuristics are adequate guardrails
**Assumption:** Masking emails/phones/token-like strings + truncation prevents most accidental leaks.
**Risk:** False negatives and edge cases.
**Mitigation:** Add structured allowlist logging and external review before handling sensitive verticals.

### A-0033 — Docker-first deployment is the simplest early operational path
**Assumption:** A single container per service + named volume is enough for early pilots.
**Risk:** Scaling and multi-tenant needs may require external DB and orchestration.
**Mitigation:** Keep compose profiles modular; add Postgres/Redis services as separate profiles when needed.

### A-0034 — Single-entrypoint proxy is sufficient for first pilots
**Assumption:** One reverse proxy + basic auth for console reduces exposure risk enough for early usage.
**Risk:** Basic auth is weak if credentials leak; no MFA.
**Mitigation:** Keep console private where possible; rotate credentials; add SSO later if needed.

### A-0035 — Process-local abuse controls are enough for early pilots
**Assumption:** Token-bucket in-memory limits + optional API key reduces trivial abuse cheaply.
**Risk:** Distributed attacks or multi-instance deployments bypass limits.
**Mitigation:** Add edge throttling and (if needed) Redis-based limits for multi-instance.

### A-0036 — Metrics CIDR allowlist is sufficient for first real deployments
**Assumption:** CIDR allowlist + token reduces accidental exposure risk.
**Risk:** Misconfigured proxy headers can spoof client IP if `AE_TRUST_PROXY=1`.
**Mitigation:** Only enable trust-proxy when proxy is controlled; prefer token-only otherwise.

### A-0037 — Operators will run public-only profile for exposed deployments
**Assumption:** Exposed deployments should not include the console service at all.
**Risk:** Teams may accidentally deploy full stack and expose console surface.
**Mitigation:** Default docs to public-only profile; require explicit selection for console.
