from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from . import db, repo


@dataclass(frozen=True)
class PageKPI:
    page_id: str
    page_url: str | None
    platform: str | None
    impressions: int
    clicks: int
    spend: float
    revenue: float
    leads: int
    bookings: int

    ctr: float | None
    cpc: float | None
    cpl: float | None
    cpa: float | None
    roas: float | None
    lead_to_booking: float | None


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


def kpi_report_for_client(
    db_path: str,
    *,
    client_id: str,
    platform: str | None = None,
    since_iso: str | None = None,
    limit_pages: int = 500,
) -> Dict[str, Any]:
    """Compute a KPI report per page for a client using stored data.

    Inputs:
      - ad_stats: impressions, clicks, spend, revenue
      - lead_intake: leads (non-spam)
      - events: bookings (event_name='booking')

    Notes:
      - This is a v1 diagnostic report. It is designed to surface guardrail failures
        (tracking gaps, zero CTR, rising CPL) quickly.
    """
    pages = repo.list_pages_filtered(db_path, client_id=client_id, limit=limit_pages)
    rows: List[PageKPI] = []

    totals = {
        "impressions": 0,
        "clicks": 0,
        "spend": 0.0,
        "revenue": 0.0,
        "leads": 0,
        "bookings": 0,
    }

    for p in pages:
        s = repo.sum_ad_stats(db_path, page_id=p.page_id, since_iso=since_iso, platform=platform)
        impressions = int(s.get("impressions", 0) or 0)
        clicks = int(s.get("clicks", 0) or 0)
        spend = float(s.get("spend", 0.0) or 0.0)
        revenue = float(s.get("revenue", 0.0) or 0.0)

        leads = _count_leads(db_path, page_id=p.page_id, client_id=client_id, since_iso=since_iso)
        bookings = _count_events(db_path, page_id=p.page_id, event_name="thank_you_view", since_iso=since_iso)

        ctr = _safe_div(clicks, impressions)
        cpc = _safe_div(spend, clicks)
        cpl = _safe_div(spend, leads)
        cpa = _safe_div(spend, bookings)
        roas = _safe_div(revenue, spend)
        lead_to_booking = _safe_div(bookings, leads)

        rows.append(PageKPI(
            page_id=p.page_id,
            page_url=getattr(p, "page_url", None),
            platform=platform,
            impressions=impressions,
            clicks=clicks,
            spend=spend,
            revenue=revenue,
            leads=leads,
            bookings=bookings,
            ctr=ctr,
            cpc=cpc,
            cpl=cpl,
            cpa=cpa,
            roas=roas,
            lead_to_booking=lead_to_booking,
        ))

        totals["impressions"] += impressions
        totals["clicks"] += clicks
        totals["spend"] += spend
        totals["revenue"] += revenue
        totals["leads"] += leads
        totals["bookings"] += bookings

    summary = {
        "client_id": client_id,
        "platform": platform,
        "since_iso": since_iso,
        "pages": len(rows),
        "totals": {
            **totals,
            "ctr": _safe_div(totals["clicks"], totals["impressions"]) ,
            "cpc": _safe_div(totals["spend"], totals["clicks"]),
            "cpl": _safe_div(totals["spend"], totals["leads"]),
            "cpa": _safe_div(totals["spend"], totals["bookings"]),
            "roas": _safe_div(totals["revenue"], totals["spend"]),
            "lead_to_booking": _safe_div(totals["bookings"], totals["leads"]),
        }
    }

    def _row_to_dict(r: PageKPI) -> Dict[str, Any]:
        return {
            "page_id": r.page_id,
            "page_url": r.page_url,
            "platform": r.platform,
            "impressions": r.impressions,
            "clicks": r.clicks,
            "spend": r.spend,
            "revenue": r.revenue,
            "leads": r.leads,
            "bookings": r.bookings,
            "ctr": r.ctr,
            "cpc": r.cpc,
            "cpl": r.cpl,
            "cpa": r.cpa,
            "roas": r.roas,
            "lead_to_booking": r.lead_to_booking,
        }

    return {"summary": summary, "rows": [_row_to_dict(r) for r in rows]}
