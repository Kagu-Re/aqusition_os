# Abuse controls (v4)

This release adds lightweight guardrails for public-facing deployments.

## Controls
### 1) Optional API key
- If `AE_API_KEY` is set:
  - requests to public endpoints require header `X-Api-Key: <AE_API_KEY>`
- If not set: no API key is required.

### 2) Request size cap
- `AE_MAX_BODY_BYTES` (default `1_000_000`)
- Blocks requests with `Content-Length` above the cap (HTTP 413)

### 3) Rate limiting (process-local)
Token bucket per client key:
- Key = client IP if available, else `X-Request-ID`, else `"anon"`
- `AE_RATE_LIMIT_RPS` (default `1.5`)
- `AE_RATE_LIMIT_BURST` (default `10`)

Returns:
- HTTP 429 with `{ "error": "rate_limited" }`

## Notes
- This is in-memory and resets on restart.
- For real production exposure:
  - prefer edge rate limiting (CDN/WAF/gateway)
  - consider centralized limiting (Redis) if needed.

## Per-route costs
Rate limiting uses a token cost per request:
- `AE_RL_COST_LEAD_INTAKE` (default 3.0)
- `AE_RL_COST_ADMIN` (default 1.5)
- `AE_RL_COST_DEFAULT` (default 1.0)
- `/metrics` and `/health` cost 0.2

## Trusted proxy mode
If you run behind a reverse proxy and want real client IPs:
- set `AE_TRUST_PROXY=1`
- middleware uses `X-Forwarded-For` (first hop) for client keying.
