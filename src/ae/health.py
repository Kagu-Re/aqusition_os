from __future__ import annotations

import os
import time
from typing import Any, Dict

from fastapi import APIRouter

from . import __version__
from .storage import resolve_db_path


def _env_bool(key: str, default: bool = False) -> bool:
    v = os.getenv(key)
    if v is None or v.strip() == "":
        return default
    return v.strip().lower() in ("1","true","yes","y")


_started = time.time()

router = APIRouter(tags=["health"])


def _uptime_s() -> float:
    return max(0.0, time.time() - _started)


def _db_ok() -> Dict[str, Any]:
    """SQLite reachability check. Non-invasive: open + simple pragma."""
    path = resolve_db_path(default_path="data/acq.db")
    try:
        import sqlite3

        con = sqlite3.connect(path, timeout=1.0)
        try:
            con.execute("PRAGMA quick_check;")
        finally:
            con.close()
        d = {"ok": True, "kind": "sqlite"}
        if _env_bool("AE_HEALTH_SHOW_DB_PATH", False) or (os.getenv("AE_ENV", "").strip().lower() != "prod"):
            d["path"] = path
        return d
    except Exception as e:
        d = {"ok": False, "kind": "sqlite", "error": str(e)[:300]}
        if _env_bool("AE_HEALTH_SHOW_DB_PATH", False) or (os.getenv("AE_ENV", "").strip().lower() != "prod"):
            d["path"] = path
        return d


@router.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": "acq-engine",
        "version": __version__,
        "uptime_s": round(_uptime_s(), 3),
        "db": _db_ok(),
    }


@router.get("/ready")
def ready() -> Dict[str, Any]:
    db = _db_ok()
    ok = bool(db.get("ok"))
    return {
        "ok": ok,
        "service": "acq-engine",
        "version": __version__,
        "db": db,
    }
