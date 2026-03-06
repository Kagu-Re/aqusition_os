from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import Response

from . import repo
from .console_support import require_secret, _resolve_db

router = APIRouter()

@router.get("/api/abuse")
def api_abuse(
    request: Request,
    db: str | None = None,
    since: str | None = None,
    reason: str | None = None,
    endpoint_prefix: str | None = None,
    limit: int = 200,
):
    require_secret(request)
    db_path = _resolve_db(db)
    return repo.list_abuse(
        db_path,
        since_ts=since,
        reason=reason,
        endpoint_prefix=endpoint_prefix,
        limit=limit,
    )

@router.get("/api/abuse/export")
def api_abuse_export(
    request: Request,
    db: str | None = None,
    since: str | None = None,
    reason: str | None = None,
    endpoint_prefix: str | None = None,
    limit: int = 2000,
):
    require_secret(request)
    db_path = _resolve_db(db)
    csv_text = repo.export_abuse_csv(
        db_path,
        since_ts=since,
        reason=reason,
        endpoint_prefix=endpoint_prefix,
        limit=limit,
    )
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=abuse_log.csv"},
    )


@router.post("/api/blocklist/add")
async def api_blocklist_add(
    request: Request,
    key: str,
    ttl_s: int = 900,
):
    """Add a short-lived dynamic block (Redis required).

    `key` should typically be the client IP. The abuse middleware uses IP as the primary client key.
    """
    require_secret(request)
    from .abuse_controls import blocklist_add

    ok = await blocklist_add(key.strip(), ttl_s=int(ttl_s))
    if not ok:
        return {"error": "redis_not_configured"}
    return {"ok": True, "key": key.strip(), "ttl_s": int(ttl_s)}


@router.post("/api/blocklist/remove")
async def api_blocklist_remove(
    request: Request,
    key: str,
):
    """Remove a dynamic block (Redis required)."""
    require_secret(request)
    from .abuse_controls import blocklist_remove

    ok = await blocklist_remove(key.strip())
    if not ok:
        return {"error": "redis_not_configured"}
    return {"ok": True, "key": key.strip()}


@router.get("/api/blocklist/ttl")
async def api_blocklist_ttl(
    request: Request,
    key: str,
):
    """Return TTL (seconds) for a dynamic block key (Redis required)."""
    require_secret(request)
    from .abuse_controls import blocklist_ttl

    ttl = await blocklist_ttl(key.strip())
    if ttl is None:
        return {"error": "redis_not_configured_or_missing"}
    return {"ok": True, "key": key.strip(), "ttl_s": int(ttl)}
