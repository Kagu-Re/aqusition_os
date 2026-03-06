from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Dict

from fastapi import HTTPException, Request

from .settings import get_settings


def _is_prod() -> bool:
    v = (os.getenv("AE_ENV") or "").strip().lower()
    if v in ("prod", "production"):
        return True
    req = (os.getenv("AE_REQUIRE_SECRET") or "").strip().lower()
    return req in ("1", "true", "yes", "y")

# In-memory rate limiter for public endpoints (single-process).
# If you run multiple workers, prefer an edge/WAF limit or Redis-backed limiter.

@dataclass
class Bucket:
    tokens: float
    last_ts: float

_BUCKETS: Dict[str, Bucket] = {}


def get_cors_allowlist() -> list[str]:
    """Return CORS origins list from settings.

    Env: AE_PUBLIC_CORS_ORIGINS (comma-separated), default '*'
    In prod: restricts to explicit origins only; '*' is rejected for security.
    """
    origins = get_settings().public_cors_origins
    if _is_prod() and ("*" in origins or not origins):
        return []  # Prod requires explicit origins; empty => no CORS (or use AE_PUBLIC_CORS_ORIGINS)
    return origins


def rate_limit_or_429(request: Request) -> None:
    """Token-bucket limiter per coarse IP. Raises 429 if exceeded.

    Env:
    - AE_LEAD_RL_PER_MIN: refill rate per minute (default 30; prod default 10 when not set)
    - AE_LEAD_RL_BURST: max burst capacity (default 60; prod default 20 when not set)
    """
    s = get_settings()
    if _is_prod() and os.getenv("AE_LEAD_RL_PER_MIN") is None and os.getenv("AE_LEAD_RL_BURST") is None:
        per_min = 10.0
        burst = 20.0
    else:
        per_min = float(s.lead_rl_per_min)
        burst = float(s.lead_rl_burst)
    if per_min <= 0 or burst <= 0:
        return  # disabled

    now = time.time()
    ip = ""
    if request.client and request.client.host:
        ip = request.client.host

    # coarse key (IPv4 /24), else fallback to UA
    key = ip
    if ip and "." in ip:
        parts = ip.split(".")
        if len(parts) == 4:
            key = ".".join(parts[:3] + ["0"])
    if not key:
        key = f"ua:{(request.headers.get('user-agent') or '')[:80]}"

    b = _BUCKETS.get(key)
    if b is None:
        b = Bucket(tokens=burst, last_ts=now)
        _BUCKETS[key] = b

    # refill
    elapsed = max(0.0, now - b.last_ts)
    refill_per_sec = per_min / 60.0
    b.tokens = min(burst, b.tokens + elapsed * refill_per_sec)
    b.last_ts = now

    if b.tokens < 1.0:
        raise HTTPException(status_code=429, detail="rate_limited")
    b.tokens -= 1.0
