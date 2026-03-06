from __future__ import annotations

import json
import os
import time
import uuid
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .settings import get_settings
from .metrics import record_request
from .log_safety import sanitize_text, safe_client_ip


def _env_bool(key: str, default: bool = False) -> bool:
    v = os.getenv(key)
    if v is None or v.strip() == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "y")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Injects X-Request-ID and logs basic request metrics.

    - Incoming: honors X-Request-ID if present (and sane), else generates UUID4.
    - Outgoing: sets X-Request-ID response header.
    - Logging: single-line JSON log (stdout) unless disabled.

    Env:
    - AE_LOG_REQUESTS=1 (default 1)
    - AE_LOG_BODY=0 (default 0) (kept off; do NOT log lead bodies)
    """

    async def dispatch(self, request: Request, call_next: Callable):
        start = time.time()

        rid = (request.headers.get("x-request-id") or "").strip()
        if not rid or len(rid) > 64:
            rid = str(uuid.uuid4())

        # attach to request state for handlers
        request.state.request_id = rid

        status = 500
        try:
            response: Response = await call_next(request)
            status = response.status_code
        except Exception:
            # log then re-raise
            status = 500
            self._log(request, status, start, rid, error="unhandled_exception")
            raise

        # attach to response
        response.headers["X-Request-ID"] = rid

        self._log(request, status, start, rid, error=None)
        return response

    def _log(self, request: Request, status: int, start: float, rid: str, error: Optional[str]):
        if not _env_bool("AE_LOG_REQUESTS", True):
            return
        ms = (time.time() - start) * 1000.0
        record_request(request.method, request.url.path, status, ms)
        payload = {
            "ts": round(time.time(), 3),
            "rid": rid,
            "svc": os.getenv("AE_SERVICE_NAME", getattr(getattr(request, "app", None), "title", "ae")),
            "method": request.method,
            "path": request.url.path,
            "status": status,
            "ms": round(ms, 2),
            "client": getattr(request.client, "host", "") if request.client else "",
            "error": error,
        }
        tid = getattr(request.state, "tenant_id", None)
        if tid:
            payload["tenant_id"] = tid
        # keep logs compact + stable
        print(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))
