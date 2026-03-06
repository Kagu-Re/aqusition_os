"""Tenant resolution middleware. Runs early to set request.state.tenant_id."""
from __future__ import annotations

from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from .config import is_multi_tenant_enabled


def _resolve_tenant_from_request(request: Request) -> Optional[str]:
    """Resolve tenant from X-Tenant-ID, subdomain, or path. Returns None if not found."""
    # 1) Header (explicit, highest precedence)
    h = (request.headers.get("X-Tenant-ID") or "").strip()
    if h:
        return h

    # 2) Subdomain (e.g. tenant1.example.com)
    host = (request.headers.get("host") or "").split(":")[0]
    if host and "." in host:
        parts = host.split(".")
        # Skip "www" - next part is tenant
        start = 1 if parts[0].lower() == "www" else 0
        if len(parts) > start + 1:
            sub = parts[start].strip()
            if sub and sub.lower() not in ("localhost", "127", "api", "www"):
                return sub

    # 3) Path prefix (e.g. /t/tenant1/... or /tenant1/...)
    path = (request.scope.get("path") or "").strip()
    if path.startswith("/t/"):
        rest = path[3:].lstrip("/")
        tenant = rest.split("/", 1)[0].strip() if rest else None
        if tenant:
            return tenant

    return None


class TenantResolutionMiddleware(BaseHTTPMiddleware):
    """Sets request.state.tenant_id when multi-tenant is enabled."""

    async def dispatch(self, request: Request, call_next):
        if not is_multi_tenant_enabled():
            request.state.tenant_id = None
        else:
            tenant_id = _resolve_tenant_from_request(request)
            request.state.tenant_id = tenant_id
        return await call_next(request)
