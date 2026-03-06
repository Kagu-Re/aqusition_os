"""Request-scoped tenant context."""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, Request

from .config import is_multi_tenant_enabled


def get_tenant_id_from_request(request: Request) -> Optional[str]:
    """Read tenant_id from request.state (set by middleware). Returns None if not set."""
    return getattr(request.state, "tenant_id", None)


def get_tenant_id(request: Request) -> Optional[str]:
    """Alias for get_tenant_id_from_request."""
    return get_tenant_id_from_request(request)


def get_scoped_client_id(request: Request) -> Optional[str]:
    """When multi-tenant enabled and tenant resolved: returns tenant_id (used as client_id).
    Otherwise returns None (no scoping; single-tenant or tenant not resolved)."""
    if not is_multi_tenant_enabled():
        return None
    return get_tenant_id_from_request(request)


def get_verified_tenant_id(request: Request, *, raise_on_mismatch: bool = True) -> Optional[str]:
    """Return tenant_id only when bound to authentication (session or API key).
    When session-scoped: uses session.tenant_id; validates X-Tenant-ID matches or is absent.
    When X-AE-SECRET admin: uses X-Tenant-ID (trusted caller).
    When API key: uses key's tenant_id; validates X-Tenant-ID matches or is absent.
    Returns None when not multi-tenant, no auth, or no tenant bound.
    Raises 403 when X-Tenant-ID conflicts with session tenant (if raise_on_mismatch=True)."""
    if not is_multi_tenant_enabled():
        return None

    from ..auth import get_user_and_tenant_for_session
    from ..api_keys import get_api_key_from_request, lookup_tenant_for_api_key
    from ..console_support import _auth_db_path, _get_bearer_token, _get_secret

    header_tid = (request.headers.get("X-Tenant-ID") or "").strip() or None

    # X-AE-SECRET admin bypass: trusted; use header tenant
    secret = (_get_secret() or "").strip()
    if secret:
        got = (request.headers.get("X-AE-SECRET") or "").strip()
        if got and got == secret:
            return header_tid

    # API key: use key's tenant_id
    api_key = get_api_key_from_request(request)
    if api_key:
        key_tid = lookup_tenant_for_api_key(_auth_db_path(), api_key)
        if key_tid:
            if header_tid and header_tid != key_tid and raise_on_mismatch:
                raise HTTPException(status_code=403, detail="tenant_mismatch")
            return key_tid

    # Session: use session's tenant_id; validate header
    sid = _get_bearer_token(request) or (request.cookies.get("ae_session") or "").strip()
    if sid:
        user, session_tid = get_user_and_tenant_for_session(_auth_db_path(), sid)
        if user and session_tid:
            if header_tid and header_tid != session_tid and raise_on_mismatch:
                raise HTTPException(status_code=403, detail="tenant_mismatch")
            return session_tid
        if user and header_tid:
            # Legacy session without tenant_id: allow header
            return header_tid

    return None
