from __future__ import annotations
from typing import Any, Dict
from .interfaces import AnalyticsAdapter

class DbAnalyticsAdapter(AnalyticsAdapter):
    """Reads events from the internal DB."""

    def __init__(self, repo_module):
        self.repo = repo_module

    def summary(self, page_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        db_path = context["db_path"]
        events = self.repo.list_events(db_path, page_id=page_id)
        counts: Dict[str, int] = {}
        for e in events:
            counts[e.event_name] = counts.get(e.event_name, 0) + 1
        return {"page_id": page_id, "events_total": len(events), "events_by_name": counts}


    def kpis(self, page_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Normalized KPI view.

        Notes:
        - If top-of-funnel inputs (impressions/clicks/spend/revenue) are absent, derived metrics become null.
        - Events are treated as in-site funnel signals:
          - leads: call_click + quote_submit
          - bookings: thank_you_view (proxy)
        """
        db_path = context["db_path"]
        events = self.repo.list_events(db_path, page_id=page_id)

        counts: Dict[str, int] = {}
        for e in events:
            counts[e.event_name] = counts.get(e.event_name, 0) + 1

        impressions = context.get("impressions")
        clicks = context.get("clicks")
        spend = context.get("spend")
        revenue = context.get("revenue")

        # fallback: if not provided, try pulling from ad_stats (last 30d by default)
        if impressions is None and clicks is None and spend is None and revenue is None:
            since_iso = context.get("since_iso")
            if since_iso is None:
                # naive horizon: caller can override; keep it simple here.
                since_iso = "1970-01-01T00:00:00"
            plat = context.get("platform")
            sums = self.repo.sum_ad_stats(db_path, page_id=page_id, since_iso=since_iso, platform=plat)
            if sums:
                impressions = sums.get("impressions")
                clicks = sums.get("clicks")
                spend = sums.get("spend")
                revenue = sums.get("revenue")

        def _rate(a, b):
            try:
                if a is None or b in (None, 0):
                    return None
                return float(a) / float(b)
            except Exception:
                return None

        call_click = counts.get("call_click", 0)
        quote_submit = counts.get("quote_submit", 0)
        thank_you_view = counts.get("thank_you_view", 0)

        leads = call_click + quote_submit
        bookings = thank_you_view

        kpis = {
            "impressions": impressions,
            "clicks": clicks,
            "spend": spend,
            "revenue": revenue,
            "events": counts,
            "leads": leads,
            "bookings": bookings,
            # core rates
            "ctr": _rate(clicks, impressions),                 # clicks / impressions
            "lead_rate": _rate(leads, clicks),                 # leads / clicks
            "booking_rate": _rate(bookings, clicks),           # bookings / clicks
            "lead_to_booking_rate": _rate(bookings, leads),    # bookings / leads
            # unit economics
            "cpc": _rate(spend, clicks),                       # spend / clicks
            "cpl": _rate(spend, leads),                        # spend / leads
            "cpa": _rate(spend, bookings),                     # spend / bookings
            "aov": _rate(revenue, bookings),                   # revenue / bookings
            "roas": _rate(revenue, spend),                     # revenue / spend
        }

        return {
            "page_id": page_id,
            "kpis": kpis,
            "definitions": {
                "ctr": "clicks / impressions",
                "lead_rate": "leads / clicks",
                "booking_rate": "bookings / clicks",
                "lead_to_booking_rate": "bookings / leads",
                "cpc": "spend / clicks",
                "cpl": "spend / leads",
                "cpa": "spend / bookings",
                "aov": "revenue / bookings",
                "roas": "revenue / spend",
                "leads": "call_click + quote_submit",
                "bookings": "thank_you_view (proxy)",
            },
        }
