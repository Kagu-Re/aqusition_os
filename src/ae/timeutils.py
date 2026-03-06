from __future__ import annotations
from datetime import datetime, timedelta, timezone


def window_to_since_iso(window: str | None) -> str | None:
    """Convert window like '7d','30d','90d' into since_iso UTC timestamp."""
    if not window:
        return None

    w = window.strip().lower()
    now = datetime.now(timezone.utc)

    if w.endswith("d"):
        days = int(w[:-1])
        return (now - timedelta(days=days)).isoformat()

    if w.endswith("h"):
        hours = int(w[:-1])
        return (now - timedelta(hours=hours)).isoformat()

    raise ValueError("window must be like '7d','30d','24h'")


def parse_utc(s: str) -> datetime:
    """Parse ISO-8601 UTC string (supports trailing 'Z')."""
    if s is None:
        raise ValueError("timestamp is None")
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
