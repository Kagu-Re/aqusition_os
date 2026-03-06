"""Tenant-scoped API keys for public endpoints (S3)."""
from __future__ import annotations

import hashlib
import os
from typing import Optional

from fastapi import HTTPException


def _hash_key(raw: str) -> str:
    """SHA-256 hash of the raw API key for storage/lookup."""
    return hashlib.sha256(raw.strip().encode("utf-8")).hexdigest()


def lookup_tenant_for_api_key(auth_db_path: str, raw_key: str) -> Optional[str]:
    """Look up tenant_id for a valid API key. Returns None if invalid or not found.
    Uses auth DB (same as sessions) where api_keys table lives."""
    key = (raw_key or "").strip()
    if not key:
        return None
    from .db import connect, init_db

    init_db(auth_db_path)
    kh = _hash_key(key)
    with connect(auth_db_path) as conn:
        row = conn.execute(
            "SELECT tenant_id FROM api_keys WHERE key_hash = ?",
            (kh,),
        ).fetchone()
    if not row:
        return None
    return (row[0] or "").strip() or None


def create_api_key(auth_db_path: str, tenant_id: str, name: str, raw_key: Optional[str] = None) -> str:
    """Create an API key for a tenant. Returns the raw key (only shown once).
    If raw_key not provided, generates a secure random key."""
    import secrets

    raw = raw_key or ("ae_" + secrets.token_urlsafe(32))
    kh = _hash_key(raw)
    from datetime import datetime, timezone
    from .db import connect, init_db

    init_db(auth_db_path)
    now = datetime.now(timezone.utc).isoformat()
    with connect(auth_db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO api_keys (key_hash, tenant_id, name, created_at) VALUES (?, ?, ?, ?)",
            (kh, tenant_id.strip(), (name or "default").strip(), now),
        )
    return raw


def get_api_key_from_request(request) -> Optional[str]:
    """Extract API key from X-AE-API-KEY or Authorization: Bearer."""
    h = (request.headers.get("X-AE-API-KEY") or "").strip()
    if h:
        return h
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return None


def is_api_key_required() -> bool:
    """True when AE_ENV=prod and AE_REQUIRE_API_KEY_PUBLIC=1.
    Public endpoints then require X-AE-API-KEY or Bearer token."""
    env = (os.getenv("AE_ENV") or "").strip().lower()
    if env not in ("prod", "production"):
        return False
    req = (os.getenv("AE_REQUIRE_API_KEY_PUBLIC") or "").strip().lower()
    return req in ("1", "true", "yes", "y")


def ensure_api_key_or_401(request) -> None:
    """If is_api_key_required(): raise 401 when no valid API key.
    Call after resolve_tenant_for_public_request on public routes."""
    if not is_api_key_required():
        return
    api_key = get_api_key_from_request(request)
    if not api_key:
        raise HTTPException(status_code=401, detail="api_key_required")
    from .console_support import _auth_db_path

    tid = lookup_tenant_for_api_key(_auth_db_path(), api_key)
    if not tid:
        raise HTTPException(status_code=401, detail="invalid_api_key")


def resolve_tenant_for_public_request(request) -> None:
    """When API key present and valid, set request.state.tenant_id from key.
    Call at start of public handlers before get_scoped_client_id.
    When key absent: leaves request.state.tenant_id from middleware (X-Tenant-ID)."""
    from .tenant.config import is_multi_tenant_enabled

    if not is_multi_tenant_enabled():
        return
    api_key = get_api_key_from_request(request)
    if api_key:
        from .console_support import _auth_db_path

        tid = lookup_tenant_for_api_key(_auth_db_path(), api_key)
        if tid:
            request.state.tenant_id = tid
