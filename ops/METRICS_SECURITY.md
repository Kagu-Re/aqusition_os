# Metrics security

The `/metrics` endpoint supports two optional controls:

## 1) Token
- Set `AE_METRICS_TOKEN`
- Provide header `X-Metrics-Token: <token>`

## 2) IP allowlist (CIDR)
- Set `AE_METRICS_ALLOW_CIDRS` as a comma-separated list, e.g.:
  - `127.0.0.1/32,10.0.0.0/8`
- If set, requests outside the ranges return `{ "error": "forbidden" }`.

## Proxy mode
If you're running behind a reverse proxy and want the *real* client IP:
- set `AE_TRUST_PROXY=1`
- we use the first value in `X-Forwarded-For`.
