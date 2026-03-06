# Local Runbook (Docker-first)

This runbook starts the **Operator Console** and **Public API** locally using Docker Compose.

## Prereqs
- Docker Desktop / Docker Engine
- Compose v2

## Setup
1) From repo root:
```bash
cp .env.example .env
```

2) (Optional) edit `.env`:
- set `AE_CONSOLE_SECRET`
- set `AE_PUBLIC_CORS_ORIGINS`

## Run
```bash
docker compose up --build
```

Services:
- Console: http://localhost:8000
- Public API: http://localhost:8001

## Smoke tests
```bash
# Public lead intake (replace db if needed)
curl -s -X POST http://localhost:8001/lead \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@example.com","message":"hello","utm":{"utm_source":"test"}}' | jq .

# Console abuse export (requires X-AE-SECRET if AE_CONSOLE_SECRET is set)
```

## Stop
```bash
docker compose down
```

## Notes
- Postgres is started for future use. Current code may still default to SQLite paths.
- For production, follow `ops/DEPLOYMENT_EDGE.md`.

## Smoke test
```bash
BASE_PUBLIC=http://localhost:8001 BASE_CONSOLE=http://localhost:8000 ./ops/smoke_test.sh
```

## Docker (recommended)
```bash
docker compose up --build
```
