from __future__ import annotations
"""Adapter selection via config.

Priority:
1) explicit dict config passed to resolver
2) environment variables
3) defaults

Environment variables:
- AE_CONTENT_ADAPTER=stub
- AE_PUBLISHER_ADAPTER=local_file|framer_stub|tailwind_static|webflow_stub
- AE_ANALYTICS_ADAPTER=db

- AE_PUBLISH_OUT_DIR=exports/published        (local_file)
- AE_FRAMER_OUT_DIR=exports/framer_payloads   (framer_stub)
- AE_STATIC_OUT_DIR=exports/static_site       (tailwind_static)
- AE_WEBFLOW_OUT_DIR=exports/webflow_payloads (webflow_stub)
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass(frozen=True)
class AdapterConfig:
    content: str = "stub"
    publisher: str = "tailwind_static"
    analytics: str = "db"
    publish_out_dir: str = "exports/published"
    framer_out_dir: str = "exports/framer_payloads"
    static_out_dir: str = "exports/static_site"
    webflow_out_dir: str = "exports/webflow_payloads"

def from_env() -> AdapterConfig:
    return AdapterConfig(
        content=os.getenv("AE_CONTENT_ADAPTER", "stub").strip(),
        publisher=os.getenv("AE_PUBLISHER_ADAPTER", "tailwind_static").strip(),
        analytics=os.getenv("AE_ANALYTICS_ADAPTER", "db").strip(),
        publish_out_dir=os.getenv("AE_PUBLISH_OUT_DIR", "exports/published").strip(),
        framer_out_dir=os.getenv("AE_FRAMER_OUT_DIR", "exports/framer_payloads").strip(),
        static_out_dir=os.getenv("AE_STATIC_OUT_DIR", "exports/static_site").strip(),
        webflow_out_dir=os.getenv("AE_WEBFLOW_OUT_DIR", "exports/webflow_payloads").strip(),
    )

def merge(base: AdapterConfig, override: Optional[Dict[str, Any]] = None) -> AdapterConfig:
    if not override:
        return base
    data = dict(base.__dict__)
    for k, v in override.items():
        if v is None:
            continue
        if k not in data:
            raise KeyError(f"Unknown adapter config key: {k}")
        data[k] = v
    return AdapterConfig(**data)

# (audit) prod guard would be enforced by runtime checks
