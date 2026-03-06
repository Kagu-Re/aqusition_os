# Deployment profiles

This repo supports multiple deployment shapes via docker compose profiles.

## 1) Public API only (recommended for real exposure)
Runs:
- `api` (public endpoints)
- `proxy_public` (no console routes)

Command:
- `docker compose --profile public --profile proxy_public up --build`

Notes:
- `/metrics` should be protected using `AE_METRICS_TOKEN` and/or `AE_METRICS_ALLOW_CIDRS`.

## 2) Full stack (public + console)
Runs:
- `api`
- `console` (operator UI)
- `proxy_full` (routes /console with basic auth)

Command:
- `docker compose --profile public --profile console --profile proxy_full up --build`

Required env:
- `AE_CONSOLE_USER`
- `AE_CONSOLE_PASS_HASH` (use `caddy hash-password`)

## 3) Local dev (no proxy)
Run `api` and `console` directly via uvicorn or compose without proxy.


## Optional Redis-backed rate limiting (multi-instance)

If you run multiple API instances (or restart frequently), process-local rate limits reset per instance.
To make rate limiting consistent across replicas, set:

- `AE_REDIS_URL=redis://<host>:6379/0`
- (optional) `AE_REDIS_PREFIX=ae`
- (optional) `AE_RL_REDIS_TTL_S=3600`

When Redis is configured, `AbuseControlsMiddleware` uses an atomic Lua token-bucket per client key.
If Redis is unavailable, it falls back to the in-memory bucket.

### Optional short TTL blocklist

- Static allowlist/denylist:
  - `AE_BLOCKLIST_CIDRS=203.0.113.0/24,198.51.100.10/32`

- Dynamic short blocks (future operator hook):
  - keys: `<prefix>:bl:<client_key>` with TTL (default 900s)


## Operator commands: dynamic blocklist

If `AE_REDIS_URL` is configured, you can dynamically block a client key (typically an IP) using the operator console:

- `POST /api/blocklist/add?key=<ip>&ttl_s=900`
- `POST /api/blocklist/remove?key=<ip>`
- `GET  /api/blocklist/ttl?key=<ip>`

All of these endpoints require `X-Secret` (same as other console routes).

There is a helper CLI:

- `python ops/blocklist_cli.py add --base-url http://localhost:8000 --secret <SECRET> --key 1.2.3.4 --ttl 900`


## Auto-block (optional)

If you are exposed to abuse (e.g., bots hammering forms), you can escalate repeated **rate limit** events into a short TTL block.

Environment:

- `AE_AUTO_BLOCK_ENABLED=true|false` (default false)
- `AE_AUTO_BLOCK_RATE_LIMIT_HITS=20` (how many 429s within window triggers a block)
- `AE_AUTO_BLOCK_WINDOW_S=60` (window seconds)
- `AE_AUTO_BLOCK_TTL_S=1800` (block TTL seconds)

Behavior:

- When enabled, every time a request is rate-limited (429), the system increments a per-client-key counter.
- If the counter reaches the threshold within the window, it calls the Redis TTL blocklist (if Redis is configured), or uses local fallback counters.
- The actual blocking is always applied via the same dynamic blocklist key: `<prefix>:bl:<client_key>`.

Recommendation:
- Enable only in production.
- Start conservative (e.g., hits=50, window=60, ttl=900) and adjust based on observed traffic.


## Abuse console: top offenders (optional)

You can record **rate-limit (429)** events and query the “top offenders” from Operator Console.

Enable (recommended only in production):

- `AE_ABUSE_TOP_ENABLED=true`
- `AE_ABUSE_TOP_WINDOW_S=3600`

Notes:
- With Redis enabled, the top list is shared across instances.
- Without Redis, the list is local-only (best-effort).

Endpoint (console):

- `GET /api/abuse/top?limit=20` (requires `X-AE-SECRET`)

CLI helper:

- `python ops/abuse_top_cli.py --base-url http://localhost:8001 --secret <SECRET> --limit 20`
