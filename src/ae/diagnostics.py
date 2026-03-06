from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from . import db, repo


@dataclass(frozen=True)
class DiagnosticIssue:
    severity: str  # "crit" | "warn" | "info"
    code: str
    page_id: str | None
    message: str
    details: Dict[str, Any]


def _safe_div(n: float, d: float) -> float | None:
    if d == 0:
        return None
    return n / d


def _count_leads(db_path: str, *, page_id: str, client_id: str | None = None, since_iso: str | None = None) -> int:
    con = db.connect(db_path)
    try:
        where = ["page_id=?", "is_spam=0"]
        params: list[Any] = [page_id]
        if client_id:
            where.append("client_id=?")
            params.append(client_id)
        if since_iso:
            where.append("ts>=?")
            params.append(since_iso)
        sql = f"SELECT COUNT(1) AS c FROM lead_intake WHERE {' AND '.join(where)}"
        row = db.fetchone(con, sql, tuple(params))
        return int(row["c"] or 0) if row else 0
    finally:
        con.close()


def _count_events(db_path: str, *, page_id: str, event_name: str, since_iso: str | None = None) -> int:
    con = db.connect(db_path)
    try:
        where = ["page_id=?", "event_name=?"]
        params: list[Any] = [page_id, event_name]
        if since_iso:
            where.append("timestamp>=?")
            params.append(since_iso)
        sql = f"SELECT COUNT(1) AS c FROM events WHERE {' AND '.join(where)}"
        row = db.fetchone(con, sql, tuple(params))
        return int(row["c"] or 0) if row else 0
    finally:
        con.close()


def diagnose_client(
    db_path: str,
    *,
    client_id: str,
    platform: str | None = None,
    since_iso: str | None = None,
    limit_pages: int = 500,
    booking_event_name: str = "thank_you_view",
) -> Dict[str, Any]:
    """Detect tracking gaps & guardrail risks for a client's acquisition data plane.

    Heuristics (v1):
      - spend>0 but clicks==0 -> WARN (creative/target mismatch)
      - clicks>0 but leads==0 -> CRIT (landing/tracking/offer mismatch)
      - leads>0 but bookings==0 -> WARN (mid-funnel friction)
      - ad_stats missing entirely for a page -> INFO (not running ads or no ingestion)
      - events present but clicks==0 -> INFO (organic or tracking mismatch)

    Output:
      - list of issues with severity + codes
      - summary counts
    """
    pages = repo.list_pages_filtered(db_path, client_id=client_id, limit=limit_pages)
    issues: List[DiagnosticIssue] = []

    if not pages:
        issues.append(DiagnosticIssue(
            severity="crit",
            code="NO_PAGES",
            page_id=None,
            message="No pages found for client (cannot run diagnostics).",
            details={"client_id": client_id},
        ))
        return _finalize(client_id, platform, since_iso, issues)

    for p in pages:
        s = repo.sum_ad_stats(db_path, page_id=p.page_id, since_iso=since_iso, platform=platform)
        impressions = int(s.get("impressions", 0) or 0)
        clicks = int(s.get("clicks", 0) or 0)
        spend = float(s.get("spend", 0.0) or 0.0)

        leads = _count_leads(db_path, page_id=p.page_id, client_id=client_id, since_iso=since_iso)
        bookings = _count_events(db_path, page_id=p.page_id, event_name=booking_event_name, since_iso=since_iso)

        # Missing ingestion (ad stats all zero) heuristic
        if impressions == 0 and clicks == 0 and spend == 0.0:
            # Could still be organic; mark info if there are leads/events
            if leads > 0 or bookings > 0:
                issues.append(DiagnosticIssue(
                    severity="info",
                    code="NO_AD_STATS_BUT_CONVERSIONS",
                    page_id=p.page_id,
                    message="No ad_stats for page, but leads/bookings exist (organic or missing ingestion).",
                    details={"leads": leads, "bookings": bookings},
                ))
            else:
                issues.append(DiagnosticIssue(
                    severity="info",
                    code="NO_AD_STATS",
                    page_id=p.page_id,
                    message="No ad_stats for page (ads not running or not ingested).",
                    details={},
                ))
            continue

        if spend > 0 and clicks == 0:
            issues.append(DiagnosticIssue(
                severity="warn",
                code="SPEND_NO_CLICKS",
                page_id=p.page_id,
                message="Spend recorded but zero clicks (creative/targeting mismatch or reporting gap).",
                details={"spend": spend, "impressions": impressions},
            ))

        if clicks > 0 and leads == 0:
            issues.append(DiagnosticIssue(
                severity="crit",
                code="CLICKS_NO_LEADS",
                page_id=p.page_id,
                message="Clicks recorded but zero leads (landing/offering/tracking failure).",
                details={"clicks": clicks, "spend": spend},
            ))

        if leads > 0 and bookings == 0:
            issues.append(DiagnosticIssue(
                severity="warn",
                code="LEADS_NO_BOOKINGS",
                page_id=p.page_id,
                message="Leads exist but no booking events (mid-funnel friction or missing booking tracking).",
                details={"leads": leads, "booking_event_name": booking_event_name},
            ))

        if bookings > 0 and clicks == 0:
            issues.append(DiagnosticIssue(
                severity="info",
                code="BOOKINGS_NO_CLICKS",
                page_id=p.page_id,
                message="Bookings exist but zero clicks (organic conversions or tracking mismatch).",
                details={"bookings": bookings},
            ))

    return _finalize(client_id, platform, since_iso, issues)


def _finalize(client_id: str, platform: str | None, since_iso: str | None, issues: List[DiagnosticIssue]) -> Dict[str, Any]:
    summary = {"crit": 0, "warn": 0, "info": 0}
    for i in issues:
        if i.severity in summary:
            summary[i.severity] += 1

    return {
        "summary": {
            "client_id": client_id,
            "platform": platform,
            "since_iso": since_iso,
            "counts": summary,
            "total_issues": len(issues),
        },
        "issues": [
            {
                "severity": i.severity,
                "code": i.code,
                "page_id": i.page_id,
                "message": i.message,
                "details": i.details,
            }
            for i in issues
        ],
    }
