from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import re

from .workqueue_reader import WorkRow


ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

def parse_iso_z(s: str) -> Optional[datetime]:
    s = (s or "").strip()
    if not s:
        return None
    # accept ...+00:00Z variants by stripping trailing Z if present
    if s.endswith("Z") and "+" in s:
        s = s.replace("Z","")
    if s.endswith("Z"):
        s = s[:-1]
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class WorkAge:
    work_id: str
    patch_id: str
    client_id: str
    status: str
    assignee: str
    age_days: float
    title: str


def stale_work(rows: List[WorkRow], *, days: int) -> List[WorkAge]:
    n = now_utc()
    out: List[WorkAge] = []
    for r in rows:
        created = parse_iso_z(r.created_utc)
        if created is None:
            continue
        age = (n - created).total_seconds() / 86400.0
        if age >= days and r.status.lower() in ("open","doing","blocked"):
            out.append(WorkAge(work_id=r.work_id, patch_id=r.patch_id, client_id=r.client_id, status=r.status, assignee=r.assignee, age_days=age, title=r.title))
    out.sort(key=lambda x: x.age_days, reverse=True)
    return out


def cycle_time_days(r: WorkRow) -> Optional[float]:
    c = parse_iso_z(r.created_utc)
    d = parse_iso_z(r.done_utc)
    if c is None or d is None:
        return None
    return (d - c).total_seconds() / 86400.0


def started_to_done_days(r: WorkRow) -> Optional[float]:
    s = parse_iso_z(r.started_utc)
    d = parse_iso_z(r.done_utc)
    if s is None or d is None:
        return None
    return (d - s).total_seconds() / 86400.0


def report(rows: List[WorkRow], *, days: int = 30) -> Dict[str, Any]:
    n = now_utc()
    cutoff = n - timedelta(days=days)

    # only items created within window
    window = []
    for r in rows:
        c = parse_iso_z(r.created_utc)
        if c and c >= cutoff:
            window.append(r)

    total = len(window)
    done = [r for r in window if r.status.lower() == "done"]
    blocked = [r for r in window if r.status.lower() == "blocked"]

    ct = [cycle_time_days(r) for r in done]
    ct = [x for x in ct if x is not None]
    sd = [started_to_done_days(r) for r in done]
    sd = [x for x in sd if x is not None]

    def avg(xs: List[float]) -> Optional[float]:
        return sum(xs)/len(xs) if xs else None

    # blockers
    reasons = []
    for r in blocked:
        if "BLOCKED:" in (r.notes or ""):
            idx = r.notes.find("BLOCKED:")
            reasons.append(r.notes[idx + len("BLOCKED:"):].strip())
    # count reasons
    from collections import Counter
    top = [{"reason": k, "count": v} for k,v in Counter(reasons).most_common(5)]

    return {
        "window_days": days,
        "window_total": total,
        "done": len(done),
        "blocked": len(blocked),
        "blocked_rate": (len(blocked)/total) if total else 0.0,
        "avg_cycle_time_days": avg(ct),
        "avg_start_to_done_days": avg(sd),
        "top_blocked_reasons": top,
    }

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class CapacitySnapshot:
    total: int
    status_counts: Dict[str, int]
    open_total: int
    doing_total: int
    blocked_total: int
    open_per_client: List[Tuple[str, int]]
    doing_per_assignee: List[Tuple[str, int]]


def capacity_snapshot(rows) -> CapacitySnapshot:
    """Compute capacity stats from WorkRow list."""
    status_counts = defaultdict(int)
    open_per_client = defaultdict(int)
    doing_per_assignee = defaultdict(int)

    for r in rows:
        st = (r.status or "").strip().lower()
        status_counts[st] += 1
        if st == "open":
            open_per_client[(r.client_id or "").strip()] += 1
        if st == "doing":
            doing_per_assignee[(r.assignee or "").strip()] += 1

    # sort, keep empty keys last
    def _sort_items(d):
        items = list(d.items())
        items.sort(key=lambda x: (-x[1], x[0] == "", x[0]))
        return items

    return CapacitySnapshot(
        total=len(rows),
        status_counts=dict(status_counts),
        open_total=status_counts.get("open", 0),
        doing_total=status_counts.get("doing", 0),
        blocked_total=status_counts.get("blocked", 0),
        open_per_client=_sort_items(open_per_client),
        doing_per_assignee=_sort_items(doing_per_assignee),
    )

import math
from typing import Optional, Any


def _days(delta_seconds: Optional[float]) -> Optional[float]:
    if delta_seconds is None:
        return None
    return delta_seconds / 86400.0


def _pct(values, p: float) -> Optional[float]:
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    vals = sorted(vals)
    if len(vals) == 1:
        return float(vals[0])
    # nearest-rank percentile
    k = int(math.ceil((p / 100.0) * len(vals))) - 1
    k = max(0, min(k, len(vals) - 1))
    return float(vals[k])


def _mean(values) -> Optional[float]:
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return float(sum(vals) / len(vals))


def _median(values) -> Optional[float]:
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    vals = sorted(vals)
    mid = len(vals) // 2
    if len(vals) % 2 == 1:
        return float(vals[mid])
    return float((vals[mid - 1] + vals[mid]) / 2.0)


def flow_snapshot(rows, now_utc: str):
    """Compute flow metrics (queue/exec/cycle time) in days.

    Expects WorkItem objects with created_utc, started_utc, done_utc, status.
    """
    from .timeutils import parse_utc

    now = parse_utc(now_utc)
    queue_days = []
    exec_days = []
    cycle_days = []

    open_age_days = []
    doing_age_days = []

    for r in rows:
        created = parse_utc(r.created_utc) if r.created_utc else None
        started = parse_utc(r.started_utc) if getattr(r, "started_utc", None) else None
        done = parse_utc(r.done_utc) if getattr(r, "done_utc", None) else None

        # queue time: created->started (only if started)
        if created and started:
            queue_days.append(_days((started - created).total_seconds()))

        # exec time: started->done (only if done)
        if started and done:
            exec_days.append(_days((done - started).total_seconds()))

        # cycle time: created->done (only if done)
        if created and done:
            cycle_days.append(_days((done - created).total_seconds()))

        st = (r.status or "").strip().lower()
        if created and st == "open":
            open_age_days.append(_days((now - created).total_seconds()))
        if started and st == "doing":
            doing_age_days.append(_days((now - started).total_seconds()))

    out = {
        "queue_days": {
            "mean": _mean(queue_days),
            "median": _median(queue_days),
            "p90": _pct(queue_days, 90),
            "n": len([v for v in queue_days if v is not None]),
        },
        "exec_days": {
            "mean": _mean(exec_days),
            "median": _median(exec_days),
            "p90": _pct(exec_days, 90),
            "n": len([v for v in exec_days if v is not None]),
        },
        "cycle_days": {
            "mean": _mean(cycle_days),
            "median": _median(cycle_days),
            "p90": _pct(cycle_days, 90),
            "n": len([v for v in cycle_days if v is not None]),
        },
        "age_open_days": {
            "mean": _mean(open_age_days),
            "median": _median(open_age_days),
            "p90": _pct(open_age_days, 90),
            "n": len([v for v in open_age_days if v is not None]),
        },
        "age_doing_days": {
            "mean": _mean(doing_age_days),
            "median": _median(doing_age_days),
            "p90": _pct(doing_age_days, 90),
            "n": len([v for v in doing_age_days if v is not None]),
        },
    }
    return out


def bottleneck_flags(rows, now_utc: str, *, open_age_warn_days: int = 7, doing_age_warn_days: int = 3, per_assignee_overload: int = 3, per_client_backlog: int = 10):
    """Detect bottlenecks (non-blocking warnings)."""
    from .timeutils import parse_utc

    now = parse_utc(now_utc)
    warnings = []

    open_old = []
    doing_old = []
    per_assignee = {}
    per_client = {}

    def inc(d, k):
        d[k] = d.get(k, 0) + 1

    for r in rows:
        st = (r.status or "").strip().lower()
        if st == "doing":
            inc(per_assignee, (r.assignee or "").strip())
        if st == "open":
            inc(per_client, (r.client_id or "").strip())

        created = parse_utc(r.created_utc) if r.created_utc else None
        started = parse_utc(r.started_utc) if getattr(r, "started_utc", None) else None

        if created and st == "open":
            age = (now - created).total_seconds() / 86400.0
            if age >= open_age_warn_days:
                open_old.append((r.work_id, age, r.client_id, r.title))
        if started and st == "doing":
            age = (now - started).total_seconds() / 86400.0
            if age >= doing_age_warn_days:
                doing_old.append((r.work_id, age, r.assignee, r.title))

    open_old.sort(key=lambda x: -x[1])
    doing_old.sort(key=lambda x: -x[1])

    # overload
    for a, n in sorted(per_assignee.items(), key=lambda x: (-x[1], x[0])):
        if a and n > per_assignee_overload:
            warnings.append({
                "kind": "assignee_overload",
                "assignee": a,
                "count": n,
                "threshold": per_assignee_overload,
            })

    for c, n in sorted(per_client.items(), key=lambda x: (-x[1], x[0])):
        if c and n > per_client_backlog:
            warnings.append({
                "kind": "client_backlog",
                "client_id": c,
                "count": n,
                "threshold": per_client_backlog,
            })

    if open_old:
        warnings.append({
            "kind": "open_items_old",
            "count": len(open_old),
            "threshold_days": open_age_warn_days,
            "top": [{"work_id": wid, "age_days": round(age, 2), "client_id": cid, "title": title} for wid, age, cid, title in open_old[:10]],
        })

    if doing_old:
        warnings.append({
            "kind": "doing_items_old",
            "count": len(doing_old),
            "threshold_days": doing_age_warn_days,
            "top": [{"work_id": wid, "age_days": round(age, 2), "assignee": a, "title": title} for wid, age, a, title in doing_old[:10]],
        })

    return warnings


def sla_breaches(rows, now_utc: str, *, open_sla_days: int = 14, doing_sla_days: int = 7):
    """Return SLA breach list for open/doing items based on age in days."""
    from .timeutils import parse_utc

    now = parse_utc(now_utc)
    breaches = []

    for r in rows:
        st = (r.status or "").strip().lower()
        created = parse_utc(r.created_utc) if r.created_utc else None
        started = parse_utc(r.started_utc) if getattr(r, "started_utc", None) else None

        if st == "open" and created:
            age = (now - created).total_seconds() / 86400.0
            if age >= open_sla_days:
                breaches.append({
                    "kind": "open_sla_breach",
                    "work_id": r.work_id,
                    "client_id": r.client_id,
                    "assignee": r.assignee,
                    "age_days": round(age, 2),
                    "threshold_days": open_sla_days,
                    "title": r.title,
                })

        if st == "doing" and started:
            age = (now - started).total_seconds() / 86400.0
            if age >= doing_sla_days:
                breaches.append({
                    "kind": "doing_sla_breach",
                    "work_id": r.work_id,
                    "client_id": r.client_id,
                    "assignee": r.assignee,
                    "age_days": round(age, 2),
                    "threshold_days": doing_sla_days,
                    "title": r.title,
                })

    breaches.sort(key=lambda x: (-x.get("age_days", 0), x.get("work_id", "")))
    return breaches

# ---- HTTP_METRICS (in-memory, process-local) ---------------------------------
# This section is used by FastAPI middleware to provide a minimal `/metrics` endpoint.
# It is intentionally lightweight and does not persist across restarts.

import threading
import time
from collections import defaultdict
from typing import Tuple

try:
    from fastapi import APIRouter
except Exception:  # pragma: no cover
    APIRouter = None  # type: ignore

_http_lock = threading.Lock()
_http_started_ts = time.time()

_http_req_counts = defaultdict(int)  # (method, path, status_class) -> count
_http_latency_ms_sum = defaultdict(float)  # (method, path) -> sum
_http_latency_ms_count = defaultdict(int)  # (method, path) -> count
_http_latency_ms_max = defaultdict(float)  # (method, path) -> max

def record_request(method: str, path: str, status: int, ms: float) -> None:
    status_class = f"{int(status/100)}xx"
    key = (method.upper(), path, status_class)
    lk = (method.upper(), path)
    with _http_lock:
        _http_req_counts[key] += 1
        _http_latency_ms_sum[lk] += float(ms)
        _http_latency_ms_count[lk] += 1
        if ms > _http_latency_ms_max[lk]:
            _http_latency_ms_max[lk] = float(ms)

def http_metrics_snapshot() -> Dict[str, Any]:
    with _http_lock:
        req = [
            {"method": m, "path": p, "status_class": sc, "count": c}
            for (m, p, sc), c in sorted(_http_req_counts.items())
        ]
        lat = []
        for (m, p), cnt in sorted(_http_latency_ms_count.items()):
            s = _http_latency_ms_sum[(m, p)]
            mx = _http_latency_ms_max[(m, p)]
            lat.append({
                "method": m,
                "path": p,
                "count": cnt,
                "avg_ms": round(s / cnt, 3) if cnt else 0.0,
                "max_ms": round(mx, 3),
            })
        return {
            "since_ts": round(_http_started_ts, 3),
            "uptime_s": round(time.time() - _http_started_ts, 3),
            "requests": req,
            "latency": lat,
        }


def _request_ip(request) -> str:
    import os
    trust_proxy = os.getenv("AE_TRUST_PROXY", "0").strip().lower() in ("1","true","yes","y")
    if trust_proxy:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
    return request.client.host if request.client else ""


def _cidr_allowed(ip: str, cidrs: str) -> bool:
    import ipaddress
    ip = (ip or "").strip()
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except Exception:
        return False
    for raw in (cidrs or "").split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            net = ipaddress.ip_network(raw, strict=False)
        except Exception:
            continue
        if addr in net:
            return True
    return False

metrics_router = APIRouter(tags=["metrics"]) if APIRouter else None

if metrics_router is not None:
    from fastapi import Header, Request

    @metrics_router.get("/metrics")
    def get_metrics(request: Request, x_metrics_token: str | None = Header(default=None, alias="X-Metrics-Token")):
        import os
        from .abuse_controls import abuse_metrics_snapshot
    
        token = os.getenv("AE_METRICS_TOKEN")
        allow = os.getenv("AE_METRICS_ALLOW_CIDRS")
    
        if allow:
            ip = _request_ip(request)
            if not _cidr_allowed(ip, allow):
                return {"error": "forbidden"}
    
        if token:
            if not x_metrics_token or x_metrics_token.strip() != token:
                return {"error": "unauthorized"}
    
        return {
            "http": http_metrics_snapshot(),
            "abuse_controls": abuse_metrics_snapshot(),
        }