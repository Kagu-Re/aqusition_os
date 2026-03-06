from __future__ import annotations

import sqlite3
from typing import Optional, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .auth import AuthUser, authenticate, create_session, revoke_session
from .console_support import (
    _auth_db_path,
    _cookie_settings,
    _client_ip_hint,
    _get_bearer_token,
    require_auth_optional,
    _resolve_db,
)
from . import db as dbmod

router = APIRouter()

class LoginIn(BaseModel):
    username: str
    password: str
    ttl_hours: int = 72

class LoginOut(BaseModel):
    session_id: str
    user: dict
    expires_in_hours: int

def _tenant_id_from_request(request: Request) -> str | None:
    """Tenant for session binding: middleware state or X-Tenant-ID header."""
    tid = getattr(request.state, "tenant_id", None)
    if tid:
        return tid
    return (request.headers.get("X-Tenant-ID") or "").strip() or None


@router.post("/api/auth/login", response_model=LoginOut)
def auth_login(payload: LoginIn, request: Request):
    u = authenticate(_auth_db_path(), payload.username, payload.password)
    if not u:
        raise HTTPException(status_code=401, detail="invalid_credentials")

    tenant_id = _tenant_id_from_request(request)
    sid, csrf = create_session(
        _auth_db_path(),
        u,
        ttl_hours=int(payload.ttl_hours or 72),
        ip_hint=_client_ip_hint(request),
        user_agent=(request.headers.get("user-agent") or "")[:200],
        tenant_id=tenant_id,
    )
    out = LoginOut(
        session_id=sid,
        user={"user_id": u.user_id, "username": u.username, "role": u.role},
        expires_in_hours=int(payload.ttl_hours or 72),
    )
    resp = JSONResponse(content=out.model_dump())
    cs = _cookie_settings()
    resp.set_cookie("ae_session", sid, httponly=True, samesite=cs["samesite"], secure=cs["secure"])
    resp.set_cookie("ae_csrf", csrf, httponly=False, samesite=cs["samesite"], secure=cs["secure"])
    return resp

@router.post("/api/auth/logout")
def auth_logout(request: Request, u: AuthUser = Depends(require_auth_optional)):
    sid = _get_bearer_token(request) or (request.cookies.get("ae_session", "") or "").strip()
    if sid:
        revoke_session(_auth_db_path(), sid)
    resp = JSONResponse(content={"ok": True})
    resp.delete_cookie("ae_session")
    return resp

@router.get("/api/auth/me")
def auth_me(u: AuthUser = Depends(require_auth_optional)):
    return {"user_id": u.user_id, "username": u.username, "role": u.role}

@router.get("/healthz")
def healthz():
    """Liveness probe. No DB touch."""
    return {"status": "ok"}

@router.get("/readyz")
def readyz(db: str | None = None):
    """Readiness probe. Verifies DB connectivity."""
    db_path = _resolve_db(db)
    try:
        with dbmod.connect(db_path) as conn:
            conn.execute("SELECT 1").fetchone()
    except Exception:
        raise HTTPException(status_code=503, detail="db_unavailable")
    return {"status": "ready", "db": db_path}
