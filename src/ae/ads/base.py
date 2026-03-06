from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol, runtime_checkable


@dataclass(frozen=True)
class PullSpend:
    currency: str
    spend: float
    impressions: int
    clicks: int


@dataclass(frozen=True)
class PullResults:
    leads: int
    bookings: int
    revenue: float | None = None


@dataclass(frozen=True)
class AssetSpec:
    asset_id: str
    headline: str
    primary_text: str
    image_path: str | None = None
    destination_url: str | None = None


@runtime_checkable
class AdsAdapter(Protocol):
    platform: str  # "meta" | "google"

    def pull_spend(self, *, client_id: str, date_from: str, date_to: str) -> PullSpend:
        ...

    def pull_results(self, *, client_id: str, date_from: str, date_to: str) -> PullResults:
        ...

    def push_assets(self, *, client_id: str, assets: List[AssetSpec]) -> Dict[str, Any]:
        ...
