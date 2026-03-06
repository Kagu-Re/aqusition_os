from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import Request

from .log_safety import sanitize_text


def _utc_ts() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _safe(obj: Any) -> Any:
    # Only sanitize strings; keep structure shallow.
    if obj is None:
        return None
    if isinstance(obj, str):
        return sanitize_text(obj)
    if isinstance(obj, (int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k)[:64]: _safe(v) for k, v in list(obj.items())[:50]}
    if isinstance(obj, (list, tuple)):
        return [_safe(v) for v in list(obj)[:50]]
    return sanitize_text(str(obj))


def audit_event(action: str, request: Optional[Request] = None, meta: Optional[Dict[str, Any]] = None) -> None:
    """Emit a structured audit log line (no payloads).
    This is best-effort: failures are swallowed.

    Env:
    - AE_AUDIT_LOG=1 to enable (default 1)
    """
    try:
        if os.getenv("AE_AUDIT_LOG", "1").strip().lower() not in ("1", "true", "yes", "y"):
            return

        rid = None
        path = None
        method = None
        ip_hint = None
        if request is not None:
            rid = request.headers.get("x-request-id")
            path = request.url.path
            method = request.method
            # Coarse hint only (avoid raw IP storage)
            if request.client and request.client.host and "." in request.client.host:
                parts = request.client.host.split(".")
                if len(parts) == 4:
                    ip_hint = ".".join(parts[:3] + ["0"])

        rec = {
            "ts": _utc_ts(),
            "audit": True,
            "action": action,
            "request_id": rid,
            "path": path,
            "method": method,
            "ip_hint": ip_hint,
            "meta": _safe(meta or {}),
        }
        print(json.dumps(rec, ensure_ascii=False))
    except Exception:
        return
