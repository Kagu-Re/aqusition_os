from __future__ import annotations

from typing import Dict


SIM_META = {
    "currency": "USD",
    "spend": 120.0,
    "impressions": 18000,
    "clicks": 240,
    "leads": 9,
    "bookings": 2,
    "revenue": 400.0,
}

SIM_GOOGLE = {
    "currency": "USD",
    "spend": 180.0,
    "impressions": 9000,
    "clicks": 300,
    "leads": 12,
    "bookings": 3,
    "revenue": 750.0,
}


def get_payload(platform: str) -> Dict:
    p = (platform or "").strip().lower()
    if p == "meta":
        return dict(SIM_META)
    if p == "google":
        return dict(SIM_GOOGLE)
    raise ValueError("platform must be 'meta' or 'google'")
