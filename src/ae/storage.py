from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from .settings import get_settings


def _env_str(key: str, default: str = "") -> str:
    v = os.getenv(key)
    if v is None:
        return default
    return v.strip()


def _parse_sqlite_url(db_url: str) -> Optional[str]:
    """Parse sqlite URLs into filesystem paths.

    Supported:
      - sqlite:///absolute/path.db
      - sqlite://relative/path.db
      - sqlite:relative/path.db
      - file:/absolute/path.db

    Returns path string, or None if not sqlite.
    """
    if not db_url:
        return None
    u = db_url.strip()
    if u.startswith("sqlite:///"):
        return u[len("sqlite:///"):]
    if u.startswith("sqlite://"):
        return u[len("sqlite://"):]
    if u.startswith("sqlite:"):
        return u[len("sqlite:"):]
    if u.startswith("file:"):
        # basic file: URI support (no percent decode)
        return u[len("file:"):]
    return None


def resolve_db_path(
    *,
    default_path: str = "data/acq.db",
    tenant_id: str | None = None,
) -> str:
    """Resolve the DB path for sqlite-backed stores.

    Priority:
      1) AE_DB_URL (sqlite url variants) — when no tenant_id
      2) Settings.db_url (AE_DB_URL) (same as #1; kept for clarity)
      3) AE_DB_PATH (legacy)
      4) default_path

    When tenant_id is provided and AE_MULTI_TENANT_ENABLED=1 and AE_TENANT_DB_PER_TENANT
    is set, returns path like {AE_TENANT_DB_DIR}/acq_{tenant_id}.db (DB-per-tenant).
    """
    # DB-per-tenant mode (opt-in)
    try:
        from .tenant.config import is_multi_tenant_enabled, get_tenant_db_dir
        if tenant_id and is_multi_tenant_enabled() and _env_str("AE_TENANT_DB_PER_TENANT", "").lower() in ("1", "true", "yes", "y"):
            import re
            safe = re.sub(r"[^a-zA-Z0-9_-]", "_", tenant_id)[:64] or "default"
            base = get_tenant_db_dir()
            return f"{base}/acq_{safe}.db"
    except ImportError:
        pass

    # AE_DB_URL is already read into settings.db_url, but allow direct env read too.
    db_url = _env_str("AE_DB_URL", "") or (get_settings().db_url or "")
    p = _parse_sqlite_url(db_url)
    if p:
        return p

    legacy = _env_str("AE_DB_PATH", "")
    if legacy:
        return legacy

    return default_path


def resolve_db_kind() -> str:
    """Return a coarse DB kind string. Currently: 'sqlite' or 'unknown'."""
    db_url = _env_str("AE_DB_URL", "") or (get_settings().db_url or "")
    if _parse_sqlite_url(db_url):
        return "sqlite"
    if _env_str("AE_DB_PATH", ""):
        return "sqlite"
    return "sqlite"


@dataclass(frozen=True)
class Storage:
    """Storage descriptor.

    For now, this is a thin wrapper around a sqlite DB path. The goal is to make
    the boundary explicit so future stores (e.g. Postgres) can slot in without
    rewriting the whole app.
    """

    db_path: str

    @classmethod
    def from_env(cls, *, default_path: str = "data/acq.db") -> "Storage":
        return cls(db_path=resolve_db_path(default_path=default_path))
