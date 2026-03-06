from __future__ import annotations

from .base import AdsAdapter
from .google_stub import GoogleAdsStub
from .meta_stub import MetaAdsStub


def get_ads_adapter(platform: str) -> AdsAdapter:
    p = (platform or "").strip().lower()
    if p == "meta":
        return MetaAdsStub()
    if p == "google":
        return GoogleAdsStub()
    raise ValueError("platform must be 'meta' or 'google'")
