# Changelog

## [7.8.0] - 2026-02-05
- OP-CRM-001C: Scheduled sync jobs for export presets (export_jobs table, cron-lite scheduler, runner/CLI, console APIs, and tests).

## [6.2.0] - 2026-02-05
- OP-CHAT-001B/001C/001D: Conversation mapping, message templates, and automation hooks/runner.

## 5.9.0
- OP-CHAT-001A: chat channel registry (chat_channels table + repo + console endpoints + tests).

## 5.8.0
- OP-PAY-001D: manual payment reconciliation UI (reconciliation table + console API endpoints + tests).


## 5.7.0
- OP-PAY-001C: payment event hooks (created/status_changed + state-driving status topics) with timeline mapping and tests.


## 5.6.0
- OP-PAY-001B: enforce payment→booking binding invariants and minimal capture guard.

All notable changes to this project will be documented in this file.

The format is based on *Keep a Changelog* and this project adheres to *Semantic Versioning*.

## [Unreleased]

## [4.2.0] - 2026-02-04
### Added
- Deployment profiles (public-only vs full stack) with separate Caddy configs.
- Logging policy doc + redaction unit tests.
### Fixed
- `docker-compose.yml` proxy service definition and profile wiring.


## [4.1.0] - 2026-02-04
### Added
- Per-route rate limit costs + trusted proxy client keying.
- Metrics allowlist via `AE_METRICS_ALLOW_CIDRS` + doc `ops/METRICS_SECURITY.md`.
- Structured audit logs for lead intake/outcome (`ae.audit`).


## [4.0.0] - 2026-02-04
### Added
- Abuse controls middleware: optional API key, request size cap, and process-local rate limiting.
- Docs: `ops/ABUSE_CONTROLS.md`.


## [3.9.0] - 2026-02-04
### Added
- Optional reverse proxy: Caddyfile + docker-compose profile `proxy`.
- Console basic auth at proxy layer; helper script `run_proxy.sh`.
- Docs: `ops/PROXY_GUIDE.md`.


## [3.8.0] - 2026-02-04
### Added
- Deployment wiring: Dockerfile, docker-compose profiles (public/console), `.env.example`, and one-command run/stop scripts.
- Deployment checklist: `ops/DEPLOYMENT_READINESS.md`.


## [3.7.0] - 2026-02-04
### Added
- Logging hygiene: PII/token redaction, optional coarse client ip logging, and log length cap.
- Optional `/metrics` protection via `AE_METRICS_TOKEN`.
- Policy docs: `ops/LOGGING_POLICY.md`.

## [3.6.0] - 2026-02-04
### Added
- Structured JSON logging.
- Request ID propagation (X-Request-ID).
- Prometheus-style /metrics endpoint.
- Observability documentation (`ops/OBSERVABILITY.md`).


## [3.5.0] - 2026-02-04
### Added
- Backup/restore utilities (`ops/scripts/backup.sh`, `restore.sh`) and retention rotation (`rotate_backups.sh`).
- Backup policy documentation (`ops/BACKUP_POLICY.md`).


## [3.4.0] - 2026-02-03
### Added
- Production policy: `env=prod` in `ops/release_meta.json` forbids `artifact.mode=skip`.
- Extended release meta schema with `env` field.


## [3.3.0] - 2026-02-03
### Added
- Reverse-proxy deployment templates (Caddy + Nginx) and `docker-compose.reverse-proxy.yml`.
- Deployment guide with production hardening checklist (`ops/DEPLOYMENT_GUIDE.md`).


## [3.2.0] - 2026-02-03
### Added
- CI artifact gate: release must include `acq_engine_vX_Y_Z.zip` **or** `ops/release_meta.json` with a documented skip reason.
- Release meta documentation: `ops/RELEASE_META.md` + `ops/release_meta.example.json`.


## [3.1.0] - 2026-02-03
### Added
- CI release gates (version/changelog/log-horizon checks).
- GitHub Actions workflow: `.github/workflows/ci.yml`.
### Changed
- Release checklist now includes “CI gates must pass” before building artifacts.
### Fixed
- N/A


## [3.0.0] - 2026-02-03
### Added
- Release mode foundation:
  - `ops/RELEASE_CHECKLIST.md` (repeatable release steps)
  - `ops/RELEASE_RULES.md` (versioning + artifact naming rules)
  - `ops/release.py` (helper to bump version + append changelog stub)

### Changed
- Standardized “release artifacts” naming convention:
  - `acq_engine_vX_Y_Z.zip`

## [2.9.0] - 2026-02-03
### Added
- Docker deployment baseline:
  - Simplified `docker-compose.yml` to run console + public on a shared SQLite volume
  - Per-service healthchecks via `/health`
  - `.env.example`

## [2.8.0] - 2026-02-03
### Added
- Observability baseline:
  - Request ID middleware (`X-Request-ID`) + JSON request logs (`AE_LOG_REQUESTS`)
  - Health payload hardening (hide DB path in prod unless `AE_HEALTH_SHOW_DB_PATH=1`)

## [2.7.0] - 2026-02-03
### Added
- Health & diagnostics endpoints (`/health`, `/ready`) for public + console
- `ops/smoke_test.sh`

## [2.6.0] - 2026-02-03
### Added
- Storage abstraction boundary (`ae.storage`) + active `AE_DB_URL` sqlite support
