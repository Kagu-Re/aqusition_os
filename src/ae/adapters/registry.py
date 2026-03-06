from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any

from .interfaces import ContentAdapter, PublisherAdapter, AnalyticsAdapter
from .content_stub import StubContentAdapter
from .publisher_local import LocalFilePublisher
from .publisher_framer_stub import FramerPublisherStub
from .publisher_tailwind_static import TailwindStaticSitePublisher
from .publisher_webflow_stub import WebflowPublisherStub
from .analytics_db import DbAnalyticsAdapter
from .config import AdapterConfig, from_env, merge

@dataclass
class AdapterBundle:
    content: ContentAdapter
    publisher: PublisherAdapter
    analytics: AnalyticsAdapter
    config: AdapterConfig

def resolve_adapters(repo_module, config_override: Optional[Dict[str, Any]] = None) -> AdapterBundle:
    cfg = merge(from_env(), config_override)

    if cfg.content == "stub":
        content = StubContentAdapter()
    else:
        raise ValueError(f"Unknown content adapter: {cfg.content}")

    if cfg.publisher == "local_file":
        publisher = LocalFilePublisher(out_dir=cfg.publish_out_dir)
    elif cfg.publisher == "framer_stub":
        publisher = FramerPublisherStub(out_dir=cfg.framer_out_dir)
    elif cfg.publisher == "tailwind_static":
        publisher = TailwindStaticSitePublisher(out_dir=cfg.static_out_dir)
    elif cfg.publisher == "webflow_stub":
        publisher = WebflowPublisherStub(out_dir=cfg.webflow_out_dir)
    else:
        raise ValueError(f"Unknown publisher adapter: {cfg.publisher}")

    if cfg.analytics == "db":
        analytics = DbAnalyticsAdapter(repo_module)
    else:
        raise ValueError(f"Unknown analytics adapter: {cfg.analytics}")

    return AdapterBundle(content=content, publisher=publisher, analytics=analytics, config=cfg)

# Back-compat alias
def default_adapters(repo_module) -> AdapterBundle:
    return resolve_adapters(repo_module, None)
