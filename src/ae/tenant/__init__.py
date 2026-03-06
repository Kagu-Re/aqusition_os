"""Multi-tenant infrastructure for Acquisition Engine.

Resolves tenant from X-Tenant-ID header, subdomain, or path. Sets request-scoped
tenant_id for db_path resolution or client_id scoping. Gated by AE_MULTI_TENANT_ENABLED.
"""
from .config import is_multi_tenant_enabled
from .middleware import TenantResolutionMiddleware
from .context import get_tenant_id, get_tenant_id_from_request, get_scoped_client_id

__all__ = [
    "is_multi_tenant_enabled",
    "TenantResolutionMiddleware",
    "get_tenant_id",
    "get_tenant_id_from_request",
    "get_scoped_client_id",
]
