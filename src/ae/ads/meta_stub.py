from __future__ import annotations

from typing import Any, Dict, List

from .base import AssetSpec, PullResults, PullSpend
from .simulation_payloads import get_payload


class MetaAdsStub:
    platform = "meta"

    def pull_spend(self, *, client_id: str, date_from: str, date_to: str) -> PullSpend:
        p = get_payload("meta")
        return PullSpend(p["currency"], float(p["spend"]), int(p["impressions"]), int(p["clicks"]))

    def pull_results(self, *, client_id: str, date_from: str, date_to: str) -> PullResults:
        p = get_payload("meta")
        return PullResults(int(p["leads"]), int(p["bookings"]), float(p["revenue"]))

    def push_assets(self, *, client_id: str, assets: List[AssetSpec]) -> Dict[str, Any]:
        return {
            "ok": True,
            "platform": self.platform,
            "client_id": client_id,
            "created": [
                {"asset_id": a.asset_id, "platform_asset_id": f"meta_{client_id}_{a.asset_id}"}
                for a in assets
            ],
        }
