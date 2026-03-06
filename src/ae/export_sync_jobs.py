from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional, Tuple


@dataclass(frozen=True)
class CronSpec:
    kind: str  # interval_minutes | interval_hours | daily
    value: int
    minute: int = 0
    hour: int = 0


def parse_cron(expr: str) -> CronSpec:
    """Parse a limited cron subset.

    Supported:
      - "*/N * * * *"  every N minutes
      - "0 */N * * *"  every N hours at minute 0
      - "M H * * *"   daily at H:M
      - "@hourly", "@daily"

    This intentional limitation avoids pulling heavy dependencies into the SSOT.
    """
    expr = (expr or "").strip()
    if expr in ("@hourly", "hourly"):
        return CronSpec(kind="interval_hours", value=1, minute=0)
    if expr in ("@daily", "daily"):
        return CronSpec(kind="daily", value=1, hour=0, minute=0)

    m = re.fullmatch(r"\*/(\d+)\s+\*\s+\*\s+\*\s+\*", expr)
    if m:
        n = int(m.group(1))
        if n <= 0:
            raise ValueError("cron interval must be > 0")
        return CronSpec(kind="interval_minutes", value=n)

    m = re.fullmatch(r"0\s+\*/(\d+)\s+\*\s+\*\s+\*", expr)
    if m:
        n = int(m.group(1))
        if n <= 0:
            raise ValueError("cron interval must be > 0")
        return CronSpec(kind="interval_hours", value=n, minute=0)

    m = re.fullmatch(r"(\d{1,2})\s+(\d{1,2})\s+\*\s+\*\s+\*", expr)
    if m:
        minute = int(m.group(1))
        hour = int(m.group(2))
        if not (0 <= minute <= 59 and 0 <= hour <= 23):
            raise ValueError("cron daily time out of range")
        return CronSpec(kind="daily", value=1, hour=hour, minute=minute)

    raise ValueError(f"Unsupported cron expression: {expr!r}")


def compute_next_run(expr: str, *, now: Optional[datetime] = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    spec = parse_cron(expr)
    if spec.kind == "interval_minutes":
        return now + timedelta(minutes=spec.value)
    if spec.kind == "interval_hours":
        return now + timedelta(hours=spec.value)
    # daily
    candidate = now.replace(hour=spec.hour, minute=spec.minute, second=0, microsecond=0)
    if candidate <= now:
        candidate = candidate + timedelta(days=1)
    return candidate
