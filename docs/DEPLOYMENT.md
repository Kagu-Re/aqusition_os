# AE Acquisition Engine — Deployment & Ops Runbook

Version: v1.3.1

This runbook assumes a **small single-tenant** deployment:
- one SQLite database file
- one operator console/API
- optional public lead intake (rate limited)

---

## 0) Quick mental model
- **Console + API**: FastAPI app (`ae.console_app:app`)
- **DB**: SQLite (path via `AE_DB_PATH`)
- **Auth** (two modes):
  1) **Session login** (recommended): `/api/auth/login` sets `ae_session` cookie
  2) **Admin bypass** (legacy): `X-AE-SECRET: <AE_CONSOLE_SECRET>`

---

## 1) Prerequisites
### Docker path (recommended)
- Docker 24+
- Docker Compose v2+

### Non-Docker path
- Python 3.12+
- Poetry (or pip)

---

## 2) Environment variables
### Required (prod)
- `AE_ENV` = `prod`
- `AE_DB_PATH` = absolute path, e.g. `/var/lib/acq_engine/acq.db`
- `AE_CONSOLE_SECRET` = strong random secret (kept server-side)

### Optional guardrails
- `AE_MAX_BODY_BYTES` (default `65536`)
- `AE_RL_LEAD_PER_HOUR` (default `30`)
- `AE_RL_API_PER_HOUR` (default `300`)

---

## 3) Create an admin user (session auth)
Session auth stores users/sessions in the same SQLite DB.

### Option A — inside Docker container
```bash
docker compose exec acq_engine python -m ae.cli auth-create-user --username admin --role admin
```

### Option B — local (Poetry)
```bash
export AE_DB_PATH=/var/lib/acq_engine/acq.db
poetry run python -m ae.cli auth-create-user --username admin --role admin
```

---

## 4) Start (Docker Compose)
1) Create `.env`:
```bash
AE_CONSOLE_SECRET=change-me-strong
```

2) Start:
```bash
docker compose build
docker compose up -d
```

Service is on:
- `http://localhost:8000/console`
- `http://localhost:8000/api/health`

---

## 5) Login flow (tablet-friendly)
1) Open console: `http://<host>:8000/console`
2) Call login (example curl):
```bash
curl -i -X POST http://<host>:8000/api/auth/login \
  -H "content-type: application/json" \
  -d '{"username":"admin","password":"<pw>"}'
```
3) Browser gets an `ae_session` cookie. API calls can also use:
- `Authorization: Bearer <session_id>`

> Note: if you keep using the legacy admin bypass, include `X-AE-SECRET: <AE_CONSOLE_SECRET>`.

---

## 6) Health & smoke checks
### Health
```bash
curl http://<host>:8000/api/health
```

### Minimal console access test (legacy secret)
```bash
curl -H "X-AE-SECRET: $AE_CONSOLE_SECRET" http://<host>:8000/console | head
```

---

## 7) Backups & restore (SQLite)
### Backup (recommended)
Stop writes (or stop container), then copy the file:
```bash
cp /var/lib/acq_engine/acq.db /var/backups/acq_engine/acq-$(date +%F).db
```

### Restore
```bash
cp /var/backups/acq_engine/acq-YYYY-MM-DD.db /var/lib/acq_engine/acq.db
```

---

## 8) Production notes
- Terminate TLS in a reverse proxy (nginx / caddy).
- Keep `AE_CONSOLE_SECRET` out of git. Use env vars or secret manager.
- If you expose **public lead intake**, keep the rate limits on and monitor activity log.
- Consider moving the DB to a dedicated volume (`/data`) with backups.

---

## 9) Troubleshooting
- **401 unauthorized**: missing cookie/token or wrong secret header.
- **403 forbidden**: user role too low (viewer vs operator/admin).
- **DB locked**: stop competing processes; ensure single writer.


## Console cookie hardening
- `AE_COOKIE_SECURE=1` to set Secure cookies (recommended behind HTTPS)
- `AE_COOKIE_SAMESITE=strict|lax|none` (default: lax)


## Versioning
Single source of truth is `pyproject.toml` (package version). Runtime `/api/health` reports `ae.__version__`.
eve`ops/VERSION.txt` mirrors releases for ops tracking.


## Secret guard (prod)
In production (`AE_ENV=prod` or `AE_REQUIRE_SECRET=1`), do not use the default secret value `change-me`. The app should refuse to start.


## SQLite reliability
The DB connection enables WAL mode and a busy timeout to reduce write-lock failures under concurrency.
