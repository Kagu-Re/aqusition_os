from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict
from .interfaces import PublisherAdapter, PublishResult

class LocalFilePublisher(PublisherAdapter):
    """Publishes by writing a JSON artifact to disk."""

    def __init__(self, out_dir: str = "exports/published"):
        self.out_dir = Path(out_dir)

    def publish(self, page_id: str, payload: Dict[str, Any], context: Dict[str, Any]) -> PublishResult:
        try:
            self.out_dir.mkdir(parents=True, exist_ok=True)
            path = self.out_dir / f"{page_id}.json"
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return PublishResult(ok=True, destination="local_file", artifact_path=str(path))
        except Exception as e:
            return PublishResult(ok=False, destination="local_file", errors=[str(e)])
