"""Tenant feature flag and configuration."""
from __future__ import annotations

import os


def is_multi_tenant_enabled() -> bool:
    """Return True if AE_MULTI_TENANT_ENABLED=1 (or true/yes/y). Default off."""
    v = (os.getenv("AE_MULTI_TENANT_ENABLED") or "").strip().lower()
    return v in ("1", "true", "yes", "y")


def get_tenant_db_dir() -> str:
    """Base directory for tenant DBs when DB-per-tenant. Default: data/"""
    return (os.getenv("AE_TENANT_DB_DIR") or "data").strip().rstrip("/")
