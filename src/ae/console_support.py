from __future__ import annotations

import os
import sqlite3

def _env_str(key: str, default: str = "") -> str:
    v = os.getenv(key)
    if v is None:
        return default
    return v.strip()

def _is_prod() -> bool:
    v = _env_str("AE_ENV", "").lower()
    if v in ("prod", "production"):
        return True
    req = _env_str("AE_REQUIRE_SECRET", "")
    return req.lower() in ("1", "true", "yes", "y")

def _default_db_path() -> str:
    # legacy compatibility: returns AE_DB_PATH (not AE_DB_URL)
    return _env_str("AE_DB_PATH", "").strip()

# Hard-fail guardrails for production deployments
if _is_prod():
    import os as _os
    if not (get_settings().console_secret or (_os.getenv("AE_CONSOLE_SECRET") or "")).strip():
        raise RuntimeError("AE_CONSOLE_SECRET must be set when AE_ENV=prod (or AE_REQUIRE_SECRET=1).")
    if not (_default_db_path() or (os.getenv("AE_DB_URL") or "").strip()):
        raise RuntimeError("AE_DB_PATH or AE_DB_URL must be set when AE_ENV=prod (or AE_REQUIRE_SECRET=1).")

from typing import Optional, Literal, Any

from fastapi import FastAPI, Depends, HTTPException, Request

from .settings import get_settings
from .storage import resolve_db_path
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse

from .auth import AuthUser, authenticate, create_session, get_user_for_session, get_user_and_tenant_for_session, revoke_session
from . import __version__


def _auth_db_path() -> str:
    # Prefer AE_DB_URL (sqlite) then AE_DB_PATH then default.
    return resolve_db_path(default_path="data/acq.db")


def _csrf_validate_session(session_id: str, token: str) -> bool:
    if not session_id or not token:
        return False
    try:
        conn = sqlite3.connect(_auth_db_path())
        cur = conn.execute("SELECT csrf_token FROM sessions WHERE session_id = ? AND (is_revoked IS NULL OR is_revoked=0)", (session_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return False
        return (row[0] or "") == token
    except Exception:
        return False




def _csrf_required() -> bool:
    # Enable CSRF checks when using cookie sessions. Safe default: ON in prod.
    env = os.getenv("AE_ENV", "").strip().lower()
    if os.getenv("AE_CSRF_REQUIRED", "").strip().lower() in ("0","false","no","n"):
        return False
    if env == "prod":
        return True
    # default on (safer) even in dev; can be disabled explicitly
    return True


def _csrf_token_from_cookie(request: Request) -> str:
    return (request.cookies.get("ae_csrf") or "").strip()


def _csrf_token_from_header(request: Request) -> str:
    return (request.headers.get("x-ae-csrf") or "").strip()

def _cookie_settings() -> dict:
    # Secure should be enabled behind HTTPS in prod
    secure = (os.getenv("AE_COOKIE_SECURE", "").strip().lower() in ("1","true","yes","y"))
    samesite = (os.getenv("AE_COOKIE_SAMESITE", "").strip().lower() or "lax")
    if samesite not in ("lax", "strict", "none"):
        samesite = "lax"
    return {"secure": secure, "samesite": samesite}
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pydantic import ConfigDict

from . import repo
from . import models, service
from .enums import PageStatus


def _get_secret() -> str:
    # single-tenant shared secret (simple, explicit). empty => auth disabled.
    return (get_settings().console_secret or '').strip()


def require_secret(request: Request) -> None:
    secret = _get_secret()
    if not secret:
        return
    got = request.headers.get("X-AE-SECRET", "").strip()
    if got != secret:
        raise HTTPException(status_code=401, detail="unauthorized")

def _client_ip_hint(request: Request) -> str:
    ip = (request.client.host if request.client else "") or ""
    if not ip:
        return ""
    parts = ip.split(".")
    if len(parts) == 4:
        return ".".join(parts[:3]) + ".0"
    return ip[:8]


def _get_bearer_token(request: Request) -> str:
    h = (request.headers.get("authorization") or "").strip()
    if h.lower().startswith("bearer "):
        return h.split(" ", 1)[1].strip()
    return ""


def require_auth(request: Request) -> AuthUser:
    # admin bypass (legacy)
    secret = _get_secret()
    if secret:
        got = request.headers.get("X-AE-SECRET", "").strip()
        if got and got == secret:
            u = AuthUser(user_id="u_secret", username="secret_admin", role="admin")
            request.state.actor = u.username
            # X-AE-SECRET is trusted; keep request.state.tenant_id from middleware/header
            return u

    sid = _get_bearer_token(request) or (request.cookies.get("ae_session", "") or "").strip()
    if not sid:
        raise HTTPException(status_code=401, detail="unauthorized")

    u, session_tid = get_user_and_tenant_for_session(_auth_db_path(), sid)
    if not u:
        raise HTTPException(status_code=401, detail="unauthorized")

    request.state.actor = u.username
    # Session-scoped tenant: overwrite middleware tenant with verified session tenant
    if session_tid:
        header_tid = (request.headers.get("X-Tenant-ID") or "").strip() or None
        if header_tid and header_tid != session_tid:
            raise HTTPException(status_code=403, detail="tenant_mismatch")
        request.state.tenant_id = session_tid
    return u


def require_auth_optional(request: Request) -> AuthUser:
    # dev ergonomics: if no secret configured and no session, allow anonymous viewer
    # In prod, never allow anonymous operator—require session or X-AE-SECRET
    secret = _get_secret()
    sid = _get_bearer_token(request) or (request.cookies.get("ae_session", "") or "").strip()
    if not secret and not sid:
        if _is_prod():
            raise HTTPException(status_code=401, detail="unauthorized")
        u = AuthUser(user_id="u_anon", username="anon", role="operator")
        request.state.actor = u.username
        return u
    return require_auth(request)


def require_role(role: str):
    order = {"viewer": 1, "operator": 2, "admin": 3}

    def _dep(u: AuthUser = Depends(require_auth_optional)) -> AuthUser:
        if order.get(u.role, 0) < order.get(role, 0):
            raise HTTPException(status_code=403, detail="forbidden")
        return u

    return _dep


def _get_resolved_db(request: Request, db_param: str | None = None) -> str:
    """Dependency-friendly: resolve db path with tenant awareness. Use Depends(_get_resolved_db)."""
    p = db_param or (request.query_params.get("db") if request else None)
    return _resolve_db_for_request(request, p)


def _resolve_db_for_request(request: Optional[Request], db_param: str | None) -> str:
    """Tenant-aware DB resolution. Uses tenant path only when AE_TENANT_DB_PER_TENANT.
    Shared DB (default): uses db_param; tenant_id scopes by client_id in app layer."""
    try:
        from .tenant.config import is_multi_tenant_enabled
        from .tenant.context import get_tenant_id_from_request
        if request and is_multi_tenant_enabled():
            tid = get_tenant_id_from_request(request)
            if tid and (os.getenv("AE_TENANT_DB_PER_TENANT") or "").strip().lower() in ("1", "true", "yes", "y"):
                return resolve_db_path(default_path="data/acq.db", tenant_id=tid)
    except ImportError:
        pass
    return _resolve_db(db_param)


def _resolve_db(db_param: str | None) -> str:
    """Resolve DB path based on environment guardrails. Use _resolve_db_for_request when tenant-aware."""
    if _is_prod():
        # In prod: single DB path, ignore request-provided db to avoid tenant/escape issues.
        return _default_db_path()
    # In dev: allow explicit db param, fallback to default if provided.
    return (db_param or _default_db_path() or "acq.db").strip()

# --- Guardrails (Q-0018): rate limiting + payload caps ---
from collections import deque
import time as _time

def _resolve_db_path(db_path: str | None, request: Optional[Request] = None) -> str:
    # Backward-compatible alias. Pass request for tenant-aware resolution.
    if request is not None:
        return _resolve_db_for_request(request, db_path)
    return _resolve_db(db_path)


_RL_STATE: dict[tuple[str, str], deque] = {}  # (ip, bucket) -> timestamps

def _env_int(key: str, default: int) -> int:
    v = os.getenv(key)
    if v is None or v.strip() == "":
        return default
    try:
        return int(v.strip())
    except Exception:
        return default

def _rate_limit_check(ip: str, bucket: str, *, limit: int, window_s: int) -> bool:
    """Return True if allowed."""
    now = _time.time()
    key = (ip, bucket)
    q = _RL_STATE.get(key)
    if q is None:
        q = deque()
        _RL_STATE[key] = q
    # drop expired
    cutoff = now - window_s
    while q and q[0] < cutoff:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(now)
    return True

def _coarse_ip_hint(ip: str) -> str:
    if ip and "." in ip:
        parts = ip.split(".")
        if len(parts) == 4:
            return ".".join(parts[:3] + ["0"])
    return ""

_MAX_BODY_BYTES = _env_int("AE_MAX_BODY_BYTES", 64 * 1024)  # 64KB default
_RL_LEAD_PER_HOUR = _env_int("AE_RL_LEAD_PER_HOUR", 30)
_RL_API_PER_HOUR = _env_int("AE_RL_API_PER_HOUR", 300)

# Explicit exports for console_app and route modules
__all__ = [
    # FastAPI types
    "FastAPI",
    "Depends",
    "HTTPException",
    "Request",
    # Response types
    "HTMLResponse",
    "FileResponse",
    "JSONResponse",
    "StaticFiles",
    # Auth functions
    "require_role",
    "require_secret",
    "require_auth",
    "require_auth_optional",
    "AuthUser",
    # DB resolution
    "_get_resolved_db",
    "_resolve_db",
    "_resolve_db_for_request",
    "_resolve_db_path",
    # Rate limiting (used by middleware)
    "_coarse_ip_hint",
    "_rate_limit_check",
    "_MAX_BODY_BYTES",
    "_RL_LEAD_PER_HOUR",
    "_RL_API_PER_HOUR",
    # Type hints
    "Optional",
    "Literal",
    "Any",
    # Repo and models (re-exported for convenience)
    "repo",
    "models",
    "service",
    "PageStatus",
    # Settings
    "get_settings",
    "resolve_db_path",
    # Auth helpers (used by route modules)
    "_auth_db_path",
    "_cookie_settings",
    "_client_ip_hint",
    "_get_bearer_token",
]
