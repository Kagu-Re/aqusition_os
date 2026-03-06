from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


@dataclass(frozen=True)
class WindowParseResult:
    window: str
    since_iso: str


def window_to_since_iso(window: str, *, now: Optional[datetime] = None) -> WindowParseResult:
    """Convert a window string like '7d' or '30d' into an ISO timestamp (UTC).

    Supported:
      - Nd where N is int days (e.g. 7d, 14d, 30d, 90d)

    Raises ValueError for invalid formats.
    """
    w = (window or "").strip().lower()
    if not w.endswith("d"):
        raise ValueError("window must be like '7d' or '30d'")

    n_str = w[:-1].strip()
    if not n_str.isdigit():
        raise ValueError("window days must be an integer (e.g. 7d, 30d)")

    days = int(n_str)
    if days <= 0 or days > 3650:
        raise ValueError("window days must be between 1 and 3650")

    if now is None:
        now = datetime.now(timezone.utc)

    since = now - timedelta(days=days)
    since_iso = since.replace(microsecond=0).isoformat()
    return WindowParseResult(window=w, since_iso=since_iso)
