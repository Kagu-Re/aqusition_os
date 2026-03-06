from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class PatchItem:
    patch_id: str
    timestamp_utc: str
    title: str
    body_md: str


def _stable_id(seed: str) -> str:
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()  # stable, short
    return h[:10]


def make_patch_item(
    *,
    client_id: str,
    platform: str | None,
    overall_status: str,
    since_iso: str | None,
    content_md: str,
) -> PatchItem:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat() + "Z"
    since_key = (since_iso or "")[:10]  # date-only to keep patch_id stable across reruns
    seed = f"{client_id}|{platform or 'all'}|{overall_status}|{since_key}"
    patch_id = "AP-" + _stable_id(seed)
    title = f"AutoPlan {overall_status}: client={client_id} platform={platform or 'all'}"
    body = f"- patch_id: `{patch_id}`\n- client_id: `{client_id}`\n- platform: `{platform or 'all'}`\n- status: **{overall_status}**\n- since_iso: `{since_iso}`\n\n" + content_md
    return PatchItem(patch_id=patch_id, timestamp_utc=now, title=title, body_md=body)


def append_patch_queue(
    patch_queue_path: str,
    item: PatchItem,
) -> None:
    p = Path(patch_queue_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    header = f"\n## {item.title} ({item.timestamp_utc})\n"
    entry = header + item.body_md.rstrip() + "\n"

    # Dedup by patch_id: if already present, do nothing
    if p.exists():
        existing = p.read_text(encoding="utf-8")
        if item.patch_id in existing:
            return

    with p.open("a", encoding="utf-8") as f:
        f.write(entry)
