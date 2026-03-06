# Observability

This project follows "small-but-useful" observability:

## 1) Request IDs
Middleware injects `X-Request-ID`:
- If client supplies it, we reuse it (sanity-checked).
- Otherwise we generate UUID4.
- Response always includes `X-Request-ID`.

This makes it possible to correlate:
- reverse proxy logs (Caddy/Nginx)
- app logs
- client errors

## 2) Structured request logs
`AE_LOG_REQUESTS=1` (default) prints **one-line JSON** per request:

Fields (stable):
- `ts` unix seconds
- `svc` service name (env `AE_SERVICE_NAME` or FastAPI title)
- `rid` request id
- `method`, `path`, `status`, `ms`
- `client` coarse client IP (best-effort)
- `error` (nullable)

## 3) Basic metrics endpoint
`GET /metrics` returns JSON counters and latency aggregates since process start:
- request counts by (method, path, status_class)
- average and max latency per (method, path)

This is intentionally minimal. If/when you need Prometheus, add:
- `/metrics/prometheus` exporter
- process metrics (CPU/mem)
- queue depths, DB latency, etc.

## Production notes
- Avoid logging PII: never log lead bodies.
- Keep `/metrics` behind the reverse proxy and/or a private network if exposed publicly.

## Logging hygiene
See `ops/LOGGING_POLICY.md` for redaction defaults and controls.
