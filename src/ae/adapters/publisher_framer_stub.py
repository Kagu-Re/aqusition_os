from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict
from .interfaces import PublisherAdapter, PublishResult
from ..schemas import registry as schema_registry

class FramerPublisherStub(PublisherAdapter):
    """Stub publisher that produces a Framer-shaped payload artifact.

    Writes a contract that a future real Framer adapter would translate into
    API calls / CMS updates. No network calls.
    """

    def __init__(self, out_dir: str = "exports/framer_payloads"):
        self.out_dir = Path(out_dir)

    def publish(self, page_id: str, payload: Dict[str, Any], context: Dict[str, Any]) -> PublishResult:
        try:
            self.out_dir.mkdir(parents=True, exist_ok=True)
            client = context.get("client")
            page = context.get("page")
            framer_contract = {
                "type": "framer.page_payload.v1",
                "page": {
                    "id": page_id,
                    "slug": getattr(page, "page_slug", None),
                    "url": getattr(page, "page_url", None),
                },
                "client": {
                    "id": getattr(client, "client_id", None),
                    "name": getattr(client, "client_name", None),
                    "trade": getattr(client, "trade", None),
                    "geo_city": getattr(client, "geo_city", None),
                },
                "components": [
                    {"component": "Hero", "props": {"headline": payload.get("headline"), "subheadline": payload.get("subheadline")}},
                    {"component": "CTA", "props": {"primary": payload.get("cta_primary"), "secondary": payload.get("cta_secondary")}},
                ],
                "sections": payload.get("sections", []),
                "meta": {"schema": "v1", "notes": "stub_artifact_only"},
            }
            ok, res = schema_registry.validate("framer.page_payload.v1", framer_contract)
            if not ok:
                return PublishResult(ok=False, destination="framer_stub", errors=res.errors)
            path = self.out_dir / f"{page_id}.framer.json"
            path.write_text(json.dumps(framer_contract, indent=2), encoding="utf-8")
            return PublishResult(ok=True, destination="framer_stub", artifact_path=str(path))
        except Exception as e:
            return PublishResult(ok=False, destination="framer_stub", errors=[str(e)])
