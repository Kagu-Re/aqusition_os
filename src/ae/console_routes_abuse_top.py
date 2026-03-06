from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from .console_support import require_secret
from .abuse_controls import blocklist_ttl, get_abuse_middleware_instance


router = APIRouter(tags=["abuse"])


@router.get("/api/abuse/top")
async def abuse_top(request: Request, limit: int = 20) -> dict[str, Any]:
    require_secret(request)
    mw = get_abuse_middleware_instance()
    if mw is None:
        return {"enabled": False, "error": "abuse_controls_not_enabled", "items": []}

    items = await mw._get_top_rate_limited(limit=int(limit))

    out = []
    for key, count, last_seen_ts in items:
        ttl = await blocklist_ttl(key)
        ttl = int(ttl or 0)
        out.append(
            {
                "key": key,
                "count": int(count),
                "last_seen_ts": last_seen_ts,
                "blocked": ttl > 0,
                "block_ttl_s": ttl,
            }
        )

    return {"enabled": True, "limit": int(limit), "items": out}
