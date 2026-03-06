from __future__ import annotations

import os
import re
from typing import Optional

_EMAIL_RE = re.compile(r"([A-Z0-9._%+-]+)@([A-Z0-9.-]+\.[A-Z]{2,})", re.IGNORECASE)
_PHONE_RE = re.compile(r"\b(\+?\d[\d\s().-]{6,}\d)\b")
_TOKEN_RE = re.compile(r"(?i)\b(bearer\s+)?([A-Z0-9._-]{24,})\b")

def _mask(s: str, keep: int = 2) -> str:
    if len(s) <= keep * 2:
        return "*" * len(s)
    return s[:keep] + ("*" * (len(s) - keep * 2)) + s[-keep:]

def sanitize_text(text: Optional[str]) -> Optional[str]:
    """Best-effort redaction for logs. Avoids obvious PII/secrets.

    This is *not* a perfect PII detector. It's a guardrail.
    """
    if text is None:
        return None
    t = str(text)

    # mask emails: a***@d***.com
    def _email_sub(m: re.Match) -> str:
        user, dom = m.group(1), m.group(2)
        return f"{_mask(user)}@{_mask(dom)}"
    t = _EMAIL_RE.sub(_email_sub, t)

    # mask phone-like sequences
    t = _PHONE_RE.sub(lambda m: _mask(m.group(1)), t)

    # mask long tokens that often appear in headers/URLs/logs
    t = _TOKEN_RE.sub(lambda m: (_mask(m.group(0)) if m.group(0) else ""), t)

    # hard cap to prevent log bombs
    max_len = int(os.getenv("AE_LOG_MAX_CHARS", "600"))
    if max_len > 0 and len(t) > max_len:
        t = t[:max_len] + "...(truncated)"
    return t

def safe_client_ip(raw_ip: Optional[str]) -> Optional[str]:
    """Optionally hide client ip (default hides)."""
    if not raw_ip:
        return None
    if os.getenv("AE_LOG_CLIENT_IP", "0").strip() not in ("1", "true", "yes", "y"):
        return None
    # still coarse: keep first 2 octets for ipv4
    if "." in raw_ip:
        parts = raw_ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.x.x"
    return raw_ip
