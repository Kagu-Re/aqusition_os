# Deployment readiness checklist

This checklist is for the first real deployment (small client / pilot).

## 0) Decide deployment mode
- [ ] Docker (recommended) vs bare metal
- [ ] Public API only vs Public + Console
- [ ] Domain + TLS termination (Caddy/Nginx/Cloudflare) or local-only

## 1) Config & secrets
- [ ] `.env` created (do not commit)
- [ ] `AE_METRICS_TOKEN` set (if `/metrics` exposed)
- [ ] CORS origins set (if used by a browser client)

## 2) Data & recovery
- [ ] Backups enabled (see `ops/BACKUP_POLICY.md`)
- [ ] Restore test performed once

## 3) Observability
- [ ] Request logs enabled (`AE_LOG_REQUESTS=1`)
- [ ] Confirm logs do not include payloads/PII (see `ops/LOGGING_POLICY.md`)
- [ ] `/metrics` reachable from ops network

## 4) Security boundaries
- [ ] Abuse controls configured (see `ops/ABUSE_CONTROLS.md`)

- [ ] Admin/console not publicly exposed (or protected behind auth)
- [ ] Rate limits at edge proxy (if public)

## 5) Smoke test
- [ ] `GET /health` returns ok
- [ ] Happy-path work item succeeds end-to-end
- [ ] Failure-path shows sanitized error and request id

## 6) Release discipline
- [ ] `ops/release_meta.json env=prod` for real prod releases
- [ ] artifacts stored (file/registry), not `skip`
