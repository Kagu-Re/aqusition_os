from __future__ import annotations

import os
import time
import threading
from dataclasses import dataclass
from typing import Dict, Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

EXEMPT_FROM_RATE_LIMIT = ("/health", "/ready", "/metrics", "/api/")

_ABUSE_MW_INSTANCES = []


def get_abuse_middleware_instance():
    """Best-effort: return the instance that likely has useful state."""
    if not _ABUSE_MW_INSTANCES:
        return None

    # Prefer an instance that has local top state populated
    for mw in reversed(_ABUSE_MW_INSTANCES):
        state = getattr(mw, "_rl_top_local", None)
        if state:
            return mw

    # Otherwise return most recent instance
    return _ABUSE_MW_INSTANCES[-1]


# Optional Redis support:
# - If AE_REDIS_URL is set and redis is installed, rate limiting becomes cross-process.
try:
    import redis.asyncio as redis_async  # type: ignore
except Exception:  # pragma: no cover
    redis_async = None


def _env_int(key: str, default: int) -> int:
    v = os.getenv(key)
    if v is None or v.strip() == "":
        return default
    return int(v.strip())


def _env_float(key: str, default: float) -> float:
    v = os.getenv(key)
    if v is None or v.strip() == "":
        return default
    return float(v.strip())


def _env_bool(key: str, default: bool) -> bool:
    v = os.getenv(key)
    if v is None or v.strip() == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "y")


def _cost_for_path(path: str) -> float:
    lead_cost = _env_float("AE_RL_COST_LEAD_INTAKE", 3.0)
    admin_cost = _env_float("AE_RL_COST_ADMIN", 1.5)
    default_cost = _env_float("AE_RL_COST_DEFAULT", 1.0)

    if path.startswith("/lead") or path.startswith("/api/lead") or path.startswith("/api/lead/"):
        return lead_cost
    if path.startswith("/api/leads") or path.startswith("/admin") or path.startswith("/api/"):
        return admin_cost
    if path.startswith("/metrics") or path.startswith("/health"):
        return 0.2
    return default_cost


@dataclass
class TokenBucket:
    capacity: float
    refill_per_s: float
    tokens: float
    last_ts: float

    def take(self, n: float = 1.0) -> bool:
        now = time.time()
        dt = max(0.0, now - self.last_ts)
        self.tokens = min(self.capacity, self.tokens + dt * self.refill_per_s)
        self.last_ts = now
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False


_abuse_lock = threading.Lock()
_abuse_counts: Dict[str, int] = {
    "requests_total": 0,
    "allowed_total": 0,
    "rate_limited_total": 0,
    "blocked_total": 0,
    "unauthorized_total": 0,
    "payload_too_large_total": 0,
    "redis_enabled": 0,
    "auto_block_total": 0,
}


def _inc(key: str, n: int = 1) -> None:
    with _abuse_lock:
        _abuse_counts[key] = int(_abuse_counts.get(key, 0)) + n


def abuse_metrics_snapshot() -> Dict[str, Any]:
    with _abuse_lock:
        return dict(_abuse_counts)


_LUA_TOKEN_BUCKET = r"""
-- KEYS[1] = bucket key
-- ARGV[1] = now (float seconds)
-- ARGV[2] = cost (float)
-- ARGV[3] = capacity (float)
-- ARGV[4] = refill_per_s (float)
-- ARGV[5] = ttl_seconds (int)

local key = KEYS[1]
local now = tonumber(ARGV[1])
local cost = tonumber(ARGV[2])
local cap = tonumber(ARGV[3])
local refill = tonumber(ARGV[4])
local ttl = tonumber(ARGV[5])

local tokens = redis.call("HGET", key, "tokens")
local last_ts = redis.call("HGET", key, "last_ts")

if not tokens then
  tokens = cap
  last_ts = now
else
  tokens = tonumber(tokens)
  last_ts = tonumber(last_ts)
  local dt = now - last_ts
  if dt < 0 then dt = 0 end
  tokens = math.min(cap, tokens + dt * refill)
  last_ts = now
end

local allowed = 0
if tokens >= cost then
  tokens = tokens - cost
  allowed = 1
end

redis.call("HSET", key, "tokens", tokens, "last_ts", last_ts)
redis.call("EXPIRE", key, ttl)

return allowed
"""


def _client_ip(request: Request) -> str:
    trust_proxy = _env_bool("AE_TRUST_PROXY", False)
    if trust_proxy:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
    return request.client.host if request.client else ""


def _client_key(request: Request) -> str:
    ip = (_client_ip(request) or "").strip()
    rid = (request.headers.get("x-request-id") or "").strip()
    return ip or rid or "anon"


def _cidr_allowed(ip: str, cidrs: str) -> bool:
    import ipaddress
    ip = (ip or "").strip()
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except Exception:
        return False
    for raw in (cidrs or "").split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            net = ipaddress.ip_network(raw, strict=False)
        except Exception:
            continue
        if addr in net:
            return True
    return False


class AbuseControlsMiddleware(BaseHTTPMiddleware):
    """Guardrails for exposed endpoints.

    Features:
    - Optional API key for public endpoints
    - Request body size cap
    - Rate limiting:
      - Local in-memory token bucket by client key
      - Optional Redis-backed token bucket (if AE_REDIS_URL is set)
    - Optional blocklist:
      - Static CIDR list via AE_BLOCKLIST_CIDRS
      - Dynamic short TTL blocks in Redis: key prefix `bl:` (future hooks)
    """

    def __init__(self, app):
        super().__init__(app)
        self.max_body_bytes = _env_int("AE_MAX_BODY_BYTES", 1_000_000)
        self.api_key = os.getenv("AE_API_KEY")  # optional
        self.rps = _env_float("AE_RATE_LIMIT_RPS", 1.5)
        self.burst = _env_float("AE_RATE_LIMIT_BURST", 10.0)
        self.enabled = _env_bool("AE_ABUSE_CONTROLS", True)

        # tests default: off unless explicitly enabled
        if os.getenv("PYTEST_CURRENT_TEST") is not None and os.getenv("AE_ABUSE_CONTROLS", "").strip() == "":
            self.enabled = False

        self._buckets: Dict[str, TokenBucket] = {}

        # Redis config
        self.redis_url = (os.getenv("AE_REDIS_URL") or "").strip()
        self.redis_prefix = (os.getenv("AE_REDIS_PREFIX") or "ae").strip()
        self.redis_ttl_s = _env_int("AE_RL_REDIS_TTL_S", 3600)

        self.blocklist_ttl_s = _env_int("AE_BLOCKLIST_TTL_S", 900)
        self.blocklist_cidrs = (os.getenv("AE_BLOCKLIST_CIDRS") or "").strip()

        self._redis = None
        self._lua = None

        if self.redis_url:
            if redis_async is None:  # pragma: no cover
                pass
            else:
                self._redis = redis_async.from_url(self.redis_url, decode_responses=True)
                self._lua = self._redis.register_script(_LUA_TOKEN_BUCKET)
                with _abuse_lock:
                    _abuse_counts["redis_enabled"] = 1

        _ABUSE_MW_INSTANCES.append(self)

    def _path_is_public(self, request: Request) -> bool:
        p = request.url.path
        return p.startswith("/api/") or p.startswith("/work/") or p.startswith("/leads/") or p.startswith("/public/")

    async def _is_blocked(self, request: Request, key: str) -> bool:
        ip = _client_ip(request)
        if self.blocklist_cidrs and _cidr_allowed(ip, self.blocklist_cidrs):
            return True
        if self._redis is None:
            return False
        bkey = f"{self.redis_prefix}:bl:{key}"
        try:
            return await self._redis.exists(bkey) == 1
        except Exception:
            return False

    async def _rate_limit_ok(self, request: Request, key: str, cost: float) -> bool:
        if self._redis is not None and self._lua is not None:
            rkey = f"{self.redis_prefix}:rl:{key}"
            try:
                allowed = await self._lua(
                    keys=[rkey],
                    args=[time.time(), float(cost), float(self.burst), float(self.rps), int(self.redis_ttl_s)],
                )
                return bool(int(allowed) == 1)
            except Exception:
                pass

        b = self._buckets.get(key)
        if b is None:
            b = TokenBucket(capacity=self.burst, refill_per_s=self.rps, tokens=self.burst, last_ts=time.time())
            self._buckets[key] = b
        return b.take(cost)

    def _auto_block_settings(self) -> tuple[bool, int, int, int]:
        enabled = _env_bool("AE_AUTO_BLOCK_ENABLED", False)
        hits = _env_int("AE_AUTO_BLOCK_RATE_LIMIT_HITS", 20)
        window_s = _env_int("AE_AUTO_BLOCK_WINDOW_S", 60)
        ttl_s = _env_int("AE_AUTO_BLOCK_TTL_S", 1800)
        return enabled, hits, window_s, ttl_s

    async def _auto_block_hit(self, key: str) -> int:
        """Record a rate-limit hit for `key` and return hit count in window."""
        enabled, _, window_s, _ = self._auto_block_settings()
        if not enabled:
            return 0

        # Redis path: shared counters across instances
        if self._redis is not None:
            ckey = f"{self.redis_prefix}:rlhits:{key}"
            try:
                n = await self._redis.incr(ckey)
                if int(n) == 1:
                    await self._redis.expire(ckey, int(window_s))
                return int(n)
            except Exception:
                pass

        # Local fallback: coarse fixed window counter (good enough for MVP)
        now = time.time()
        state = getattr(self, "_auto_block_local", None)
        if state is None:
            state = {}
            setattr(self, "_auto_block_local", state)
        entry = state.get(key)
        if entry is None:
            state[key] = (1, now)
            return 1
        count, start_ts = entry
        if now - float(start_ts) > float(window_s):
            state[key] = (1, now)
            return 1
        count = int(count) + 1
        state[key] = (count, start_ts)
        return count

    async def _maybe_auto_block(self, key: str) -> bool:
        enabled, hits, _, ttl_s = self._auto_block_settings()
        if not enabled:
            return False
        n = await self._auto_block_hit(key)
        if n >= int(hits):
            ok = await blocklist_add(key, ttl_s=int(ttl_s))
            if ok:
                _inc("auto_block_total")
            return ok
        return False

    def _abuse_top_settings(self) -> tuple[bool, int]:
        enabled = _env_bool("AE_ABUSE_TOP_ENABLED", False)
        window_s = _env_int("AE_ABUSE_TOP_WINDOW_S", 3600)
        return enabled, window_s

    async def _record_rate_limit_hit(self, key: str) -> None:
        enabled, window_s = self._abuse_top_settings()
        if not enabled:
            return

        # Redis preferred: shared across instances
        if self._redis is not None:
            zkey = f"{self.redis_prefix}:abuse:rl_top"
            try:
                # increment score
                await self._redis.zincrby(zkey, 1.0, key)
                # store last seen separately (hash)
                await self._redis.hset(f"{self.redis_prefix}:abuse:rl_seen", key, str(int(time.time())))
                # keep both keys bounded
                await self._redis.expire(zkey, int(window_s))
                await self._redis.expire(f"{self.redis_prefix}:abuse:rl_seen", int(window_s))
                return
            except Exception:
                pass

        # Local fallback: keep a small in-memory counter
        state = getattr(self, "_rl_top_local", None)
        if state is None:
            state = {}
            setattr(self, "_rl_top_local", state)
        state[key] = int(state.get(key, 0)) + 1

    async def _get_top_rate_limited(self, limit: int = 20) -> list[tuple[str, int, int | None]]:
        """Return [(key, count, last_seen_ts)]"""
        enabled, _ = self._abuse_top_settings()
        if not enabled:
            return []

        # Redis path
        if self._redis is not None:
            zkey = f"{self.redis_prefix}:abuse:rl_top"
            hkey = f"{self.redis_prefix}:abuse:rl_seen"
            try:
                items = await self._redis.zrevrange(zkey, 0, int(limit) - 1, withscores=True)
                if not items:
                    return []
                keys = [k for k,_ in items]
                seen = await self._redis.hmget(hkey, keys)
                out=[]
                for (k,score),s in zip(items, seen):
                    try:
                        last = int(s) if s else None
                    except Exception:
                        last = None
                    out.append((k, int(score), last))
                return out
            except Exception:
                pass

        # Local fallback
        state = getattr(self, "_rl_top_local", None) or {}
        # no last_seen in local fallback (None)
        items = sorted(state.items(), key=lambda kv: kv[1], reverse=True)[: int(limit)]
        return [(k, int(v), None) for k,v in items]

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.enabled:
            return await call_next(request)

        _inc("requests_total")

        key = _client_key(request)

        if await self._is_blocked(request, key):
            _inc("blocked_total")
            return JSONResponse({"error": "blocked"}, status_code=403)

        if self.api_key and self._path_is_public(request):
            got = request.headers.get("x-api-key")
            if not got or got.strip() != self.api_key:
                _inc("unauthorized_total")
                return JSONResponse({"error": "unauthorized"}, status_code=401)

        cl = request.headers.get("content-length")
        if cl:
            try:
                n = int(cl)
                if n > self.max_body_bytes:
                    _inc("payload_too_large_total")
                    return JSONResponse({"error": "payload_too_large", "max_bytes": self.max_body_bytes}, status_code=413)
            except Exception:
                pass

        cost = _cost_for_path(request.url.path)
        if any(request.url.path == p or request.url.path.startswith(p) for p in EXEMPT_FROM_RATE_LIMIT):
            ok = True
        else:
            ok = await self._rate_limit_ok(request, key, cost)
        if not ok:
            _inc("rate_limited_total")
            try:
                await self._record_rate_limit_hit(key)
            except Exception:
                pass
            try:
                await self._maybe_auto_block(key)
            except Exception:
                pass
            return JSONResponse({"error": "rate_limited"}, status_code=429)

        _inc("allowed_total")
        return await call_next(request)


async def blocklist_add(key: str, *, ttl_s: int = 900) -> bool:
    """Add a short-lived block entry to Redis (future operator hook)."""
    url = (os.getenv("AE_REDIS_URL") or "").strip()
    if not url or redis_async is None:
        return False
    prefix = (os.getenv("AE_REDIS_PREFIX") or "ae").strip()
    r = redis_async.from_url(url, decode_responses=True)
    try:
        await r.setex(f"{prefix}:bl:{key}", int(ttl_s), "1")
        return True
    finally:
        try:
            await r.close()
        except Exception:
            pass


async def blocklist_remove(key: str) -> bool:
    """Remove a dynamic block entry from Redis.

    Returns False if Redis is not configured.
    """
    url = (os.getenv("AE_REDIS_URL") or "").strip()
    if not url or redis_async is None:
        return False
    prefix = (os.getenv("AE_REDIS_PREFIX") or "ae").strip()
    r = redis_async.from_url(url, decode_responses=True)
    try:
        await r.delete(f"{prefix}:bl:{key}")
        return True
    finally:
        try:
            await r.close()
        except Exception:
            pass


async def blocklist_ttl(key: str) -> int | None:
    """Return TTL (seconds) for a dynamic block entry, or None if missing/not supported."""
    url = (os.getenv("AE_REDIS_URL") or "").strip()
    if not url or redis_async is None:
        return None
    prefix = (os.getenv("AE_REDIS_PREFIX") or "ae").strip()
    r = redis_async.from_url(url, decode_responses=True)
    try:
        ttl = await r.ttl(f"{prefix}:bl:{key}")
        if ttl is None:
            return None
        return int(ttl)
    finally:
        try:
            await r.close()
        except Exception:
            pass
