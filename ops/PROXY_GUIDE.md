# Reverse proxy guide (Caddy)

This project can run behind a single entrypoint (useful for pilots).

## What it does
- Exposes a single port: `8080 -> 80` inside Caddy
- Routes:
  - `/api/*` -> Public API container (8000)
  - `/console*` -> Console container (8001) **protected via basic auth**
  - `/health` and `/metrics` -> API container (still optionally protected via `AE_METRICS_TOKEN`)

## Setup
1) Copy env:
- `cp .env.example .env`

2) Set console password hash:
- `docker run --rm caddy:2 caddy hash-password --plaintext 'yourpass'`

Put the output in `.env`:
- `AE_CONSOLE_PASS_HASH=$2a$...`

3) Run:
- `./ops/scripts/run_proxy.sh`

## URLs
- Public API: `http://localhost:8080/api/`
- Console: `http://localhost:8080/console`

## Notes
- This is **not** production-grade security. For production:
  - terminate TLS properly (Caddy can do it with a domain)
  - restrict /metrics access
  - add rate limiting at edge (Cloudflare / gateway / WAF)
