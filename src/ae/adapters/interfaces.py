from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, runtime_checkable, List

@dataclass(frozen=True)
class PublishResult:
    ok: bool
    destination: str
    url: Optional[str] = None
    artifact_path: Optional[str] = None
    errors: Optional[List[str]] = None

@runtime_checkable
class ContentAdapter(Protocol):
    def build(self, page_id: str, context: Dict[str, Any]) -> Dict[str, Any]: ...

@runtime_checkable
class PublisherAdapter(Protocol):
    def publish(self, page_id: str, payload: Dict[str, Any], context: Dict[str, Any]) -> PublishResult: ...

@runtime_checkable
class AnalyticsAdapter(Protocol):
    def summary(self, page_id: str, context: Dict[str, Any]) -> Dict[str, Any]: ...
    def kpis(self, page_id: str, context: Dict[str, Any]) -> Dict[str, Any]: ...
