from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .interfaces import PublisherAdapter, PublishResult


class WebflowPublisherStub(PublisherAdapter):
    """Webflow publisher stub.

    Purpose:
    - Establish integration surface (contract + output artifact) without hitting Webflow API.
    - Produces a payload that *resembles* a Webflow CMS "Collection Item" create/update request.

    Notes:
    - Real Webflow integration will require:
      - site_id / collection_id mapping
      - auth token management
      - slug uniqueness checks
      - publish state (draft/live) handling
    """

    def __init__(self, out_dir: str = "exports/webflow_payloads"):
        self.out_dir = Path(out_dir)

    def publish(self, page_id: str, payload: Dict[str, Any], context: Dict[str, Any]) -> PublishResult:
        try:
            self.out_dir.mkdir(parents=True, exist_ok=True)
            # Minimal "collection item" shape; fields are generic placeholders.
            webflow_payload = {
                "page_id": page_id,
                "collection_item": {
                    "isDraft": False,
                    "isArchived": False,
                    "fields": {
                        "name": payload.get("meta", {}).get("title") or payload.get("page", {}).get("page_slug") or page_id,
                        "slug": payload.get("page", {}).get("page_slug") or page_id,
                        "seo-title": payload.get("meta", {}).get("title"),
                        "seo-description": payload.get("meta", {}).get("description"),
                        "body": payload.get("body_html") or payload.get("content", {}),
                    },
                },
                "source": "webflow_stub",
                "context": {
                    "site_id": context.get("webflow_site_id"),
                    "collection_id": context.get("webflow_collection_id"),
                },
            }
            path = self.out_dir / f"{page_id}.webflow.json"
            path.write_text(json.dumps(webflow_payload, indent=2), encoding="utf-8")
            return PublishResult(ok=True, destination="webflow_stub", artifact_path=str(path))
        except Exception as e:
            return PublishResult(ok=False, destination="webflow_stub", errors=[str(e)])
