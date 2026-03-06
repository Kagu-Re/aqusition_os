# Deployment Guide

This project supports multiple deployment modes:

1) **Local dev** (no proxy): `docker compose up --build`
2) **Reverse proxy** (recommended for public internet):
   - Caddy (automatic HTTPS)
   - Nginx (bring your own TLS)

## 1) Local dev (no proxy)
```bash
cp .env.example .env
docker compose up --build
```

- Console: http://localhost:8000
- Public:  http://localhost:8001

## 2) Reverse proxy with Caddy (recommended)
### Requirements
- Domain DNS A/AAAA points to your server
- Ports **80/443** open
- You edited `ops/deploy/caddy/Caddyfile` and replaced `example.com`

### Run
```bash
cp .env.example .env
# set AE_CONSOLE_SECRET (required for prod)
docker compose -f docker-compose.yml -f docker-compose.reverse-proxy.yml up --build
```

### Routes
- Console: `https://<domain>/console/`
- Public API: `https://<domain>/api/`
- Health: `https://<domain>/healthz`

### Notes
- Consider adding **edge basic auth** for `/console/*` in Caddyfile.
- Keep `AE_PUBLIC_CORS_ORIGINS` restrictive in production.

## 3) Reverse proxy with Nginx
Use `ops/deploy/nginx/default.conf` as a starting point.

You still need TLS termination:
- certbot on the same host, or
- a cloud load balancer that terminates TLS.

## Production hardening checklist
- [ ] Set `AE_ENV=prod`
- [ ] Set a strong `AE_CONSOLE_SECRET`
- [ ] Restrict `AE_PUBLIC_CORS_ORIGINS` to your domain
- [ ] Review rate limits (`AE_LEAD_RL_PER_MIN`, `AE_LEAD_RL_BURST`)
- [ ] Do not log PII (keep request logs minimal)
- [ ] Move from SQLite to Postgres when concurrency increases (contention risk)
