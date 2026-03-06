from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from . import repo
from .guardrails import evaluate_guardrails


@dataclass(frozen=True)
class ClientStoplight:
    client_id: str
    status: str  # PASS|WARN|FAIL
    crit: int
    warn: int
    info: int
    total_findings: int


def stoplight_dashboard(
    db_path: str,
    *,
    platform: str | None = None,
    since_iso: str | None = None,
    config_path: str = "config/guardrails.json",
    client_status: str | None = "live",
    limit_clients: int = 200,
) -> Dict[str, Any]:
    """Compute PASS/WARN/FAIL stoplights for multiple clients.

    This is the operational view: *who is safe to scale, who needs optimization,
    who must be paused due to tracking/conversion failure*.

    Notes:
      - `client_status` defaults to "live" so you don't waste time on drafts.
      - Uses evaluate_guardrails() per client; for large fleets we can add caching later.
    """
    clients = repo.list_clients(db_path, status=client_status, limit=limit_clients)
    rows: List[ClientStoplight] = []

    counts = {"PASS": 0, "WARN": 0, "FAIL": 0}

    for c in clients:
        r = evaluate_guardrails(
            db_path,
            client_id=c.client_id,
            platform=platform,
            since_iso=since_iso,
            config_path=config_path,
        )
        s = r["summary"]
        status = s["overall_status"]
        counts[status] = counts.get(status, 0) + 1
        rows.append(ClientStoplight(
            client_id=c.client_id,
            status=status,
            crit=int(s["counts"]["crit"]),
            warn=int(s["counts"]["warn"]),
            info=int(s["counts"]["info"]),
            total_findings=len(r.get("findings", [])),
        ))

    # Sort: FAIL first, then WARN, then PASS; within same by crit/warn desc
    order = {"FAIL": 0, "WARN": 1, "PASS": 2}
    rows_sorted = sorted(rows, key=lambda x: (order.get(x.status, 9), -x.crit, -x.warn, x.client_id))

    return {
        "summary": {
            "platform": platform,
            "since_iso": since_iso,
            "client_status_filter": client_status,
            "clients_evaluated": len(rows_sorted),
            "counts": counts,
        },
        "rows": [
            {
                "client_id": r.client_id,
                "status": r.status,
                "crit": r.crit,
                "warn": r.warn,
                "info": r.info,
                "total_findings": r.total_findings,
            }
            for r in rows_sorted
        ]
    }
