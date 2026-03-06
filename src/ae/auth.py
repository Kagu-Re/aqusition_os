from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from .db import connect, init_db


PBKDF2_ALG = "sha256"
PBKDF2_ITERS_DEFAULT = 200_000


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str, iters: int = PBKDF2_ITERS_DEFAULT) -> str:
    if not password:
        raise ValueError("password empty")
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac(PBKDF2_ALG, password.encode("utf-8"), salt, iters)
    return f"pbkdf2_{PBKDF2_ALG}${iters}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iters_s, salt_hex, hash_hex = stored.split("$", 3)
        if not scheme.startswith("pbkdf2_"):
            return False
        iters = int(iters_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        got = hashlib.pbkdf2_hmac(PBKDF2_ALG, password.encode("utf-8"), salt, iters)
        return hmac.compare_digest(got, expected)
    except Exception:
        return False


def new_session_id() -> str:
    return "s_" + secrets.token_urlsafe(32)


@dataclass(frozen=True)
class AuthUser:
    user_id: str
    username: str
    role: str  # admin|operator|viewer


def _ensure_db(db_path: str) -> None:
    init_db(db_path)


def create_user(db_path: str, username: str, password: str, role: str = "admin") -> str:
    _ensure_db(db_path)
    user_id = "u_" + secrets.token_urlsafe(10)
    pw = hash_password(password)
    con = connect(db_path)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO users (user_id, username, pw_hash, role, is_active, created_ts, updated_ts) VALUES (?,?,?,?,?,?,?)",
        (user_id, username.strip().lower(), pw, role, 1, _utcnow().isoformat(), _utcnow().isoformat()),
    )
    con.commit()
    con.close()
    return user_id


def set_password(db_path: str, username: str, password: str) -> int:
    _ensure_db(db_path)
    con = connect(db_path)
    cur = con.cursor()
    pw = hash_password(password)
    cur.execute(
        "UPDATE users SET pw_hash=?, updated_ts=? WHERE username=?",
        (pw, _utcnow().isoformat(), username.strip().lower()),
    )
    con.commit()
    n = cur.rowcount
    con.close()
    return n


def authenticate(db_path: str, username: str, password: str) -> Optional[AuthUser]:
    _ensure_db(db_path)
    con = connect(db_path)
    cur = con.cursor()
    row = cur.execute(
        "SELECT user_id, username, pw_hash, role, is_active FROM users WHERE username=?",
        (username.strip().lower(),),
    ).fetchone()
    con.close()
    if not row:
        return None
    if int(row["is_active"] or 0) != 1:
        return None
    if not verify_password(password, row["pw_hash"] or ""):
        return None
    return AuthUser(user_id=row["user_id"], username=row["username"], role=row["role"])


def create_session(
    db_path: str,
    user: AuthUser,
    ttl_hours: int = 72,
    ip_hint: str = "",
    user_agent: str = "",
    tenant_id: Optional[str] = None,
) -> tuple[str, str]:
    _ensure_db(db_path)
    sid = new_session_id()
    csrf = secrets.token_urlsafe(24)
    now = _utcnow()
    exp = now + timedelta(hours=ttl_hours)
    con = connect(db_path)
    cur = con.cursor()

    # Prefer storing csrf_token + tenant_id; fallback gracefully for older DBs.
    tid = (tenant_id or "").strip() or None
    try:
        cur.execute(
            "INSERT INTO sessions (session_id, user_id, created_ts, expires_ts, last_seen_ts, ip_hint, user_agent, is_revoked, csrf_token, tenant_id) "
            "VALUES (?,?,?,?,?,?,?,0,?,?)",
            (sid, user.user_id, now.isoformat(), exp.isoformat(), now.isoformat(), ip_hint, user_agent, csrf, tid),
        )
    except Exception:
        try:
            cur.execute(
                "INSERT INTO sessions (session_id, user_id, created_ts, expires_ts, last_seen_ts, ip_hint, user_agent, is_revoked, tenant_id) "
                "VALUES (?,?,?,?,?,?,?,0,?)",
                (sid, user.user_id, now.isoformat(), exp.isoformat(), now.isoformat(), ip_hint, user_agent, tid),
            )
        except Exception:
            cur.execute(
                "INSERT INTO sessions (session_id, user_id, created_ts, expires_ts, last_seen_ts, ip_hint, user_agent, is_revoked) "
                "VALUES (?,?,?,?,?,?,?,0)",
                (sid, user.user_id, now.isoformat(), exp.isoformat(), now.isoformat(), ip_hint, user_agent),
            )

    con.commit()
    con.close()
    return sid, csrf


def revoke_session(db_path: str, session_id: str) -> int:
    _ensure_db(db_path)
    con = connect(db_path)
    cur = con.cursor()
    cur.execute("UPDATE sessions SET is_revoked=1 WHERE session_id=?", (session_id,))
    con.commit()
    n = cur.rowcount
    con.close()
    return n


def get_user_and_tenant_for_session(db_path: str, session_id: str) -> tuple[Optional[AuthUser], Optional[str]]:
    """Return (AuthUser, tenant_id) for valid session. (None, None) if invalid.
    tenant_id may be None when multi-tenant is off or session has no tenant."""
    _ensure_db(db_path)
    con = connect(db_path)
    cur = con.cursor()
    row = cur.execute(
        "SELECT s.session_id, s.expires_ts, s.is_revoked, s.tenant_id, u.user_id, u.username, u.role, u.is_active "
        "FROM sessions s JOIN users u ON s.user_id=u.user_id WHERE s.session_id=?",
        (session_id,),
    ).fetchone()
    if not row:
        con.close()
        return None, None
    if int(row["is_revoked"] or 0) == 1 or int(row["is_active"] or 0) != 1:
        con.close()
        return None, None
    try:
        exp = datetime.fromisoformat(row["expires_ts"])
    except Exception:
        con.close()
        return None, None
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if _utcnow() > exp:
        con.close()
        return None, None

    try:
        cur.execute("UPDATE sessions SET last_seen_ts=? WHERE session_id=?", (_utcnow().isoformat(), session_id))
        con.commit()
    except Exception:
        pass

    tid = None
    try:
        if row["tenant_id"] and str(row["tenant_id"]).strip():
            tid = str(row["tenant_id"]).strip()
    except Exception:
        pass
    con.close()
    return AuthUser(user_id=row["user_id"], username=row["username"], role=row["role"]), tid


def get_user_for_session(db_path: str, session_id: str) -> Optional[AuthUser]:
    user, _ = get_user_and_tenant_for_session(db_path, session_id)
    return user
