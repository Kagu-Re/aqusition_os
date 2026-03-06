from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
import re


@dataclass(frozen=True)
class PatchEntry:
    patch_id: str
    title_line: str
    body_md: str
    client_id: Optional[str]
    platform: Optional[str]
    since_iso: Optional[str]


PATCH_ID_RE = re.compile(r"^##\s+(AP-[0-9a-fA-F]{10})\b", re.MULTILINE)


def _extract_client_id(body: str) -> Optional[str]:
    # heuristic: look for "client_id: <val>" in markdown
    m = re.search(r"\bclient_id\s*[:=]\s*`?([a-zA-Z0-9_-]+)`?", body)
    if m:
        return m.group(1)
    # also accept "Client: `c1`"
    m = re.search(r"\bClient\s*[:=]\s*`?([a-zA-Z0-9_-]+)`?", body)
    if m:
        return m.group(1)
    return None


def _extract_platform(body: str) -> Optional[str]:
    m = re.search(r"\bplatform\s*[:=]\s*`?([a-zA-Z0-9_-]+)`?", body)
    return m.group(1) if m else None


def _extract_since(body: str) -> Optional[str]:
    m = re.search(r"\bsince_iso\s*[:=]\s*`?([^\s`]+)`?", body)
    return m.group(1) if m else None


def read_patch_queue(path: str) -> List[PatchEntry]:
    p = Path(path)
    if not p.exists():
        return []
    txt = p.read_text(encoding="utf-8")

    # split by headings "## AP-..."
    matches = list(PATCH_ID_RE.finditer(txt))
    out: List[PatchEntry] = []
    for i, m in enumerate(matches):
        patch_id = m.group(1)
        start = m.start()
        end = matches[i+1].start() if i+1 < len(matches) else len(txt)
        chunk = txt[start:end].strip()
        lines = chunk.splitlines()
        title_line = lines[0].strip() if lines else f"## {patch_id}"
        body = "\n".join(lines[1:]).strip()
        out.append(PatchEntry(
            patch_id=patch_id,
            title_line=title_line,
            body_md=body,
            client_id=_extract_client_id(body),
            platform=_extract_platform(body),
            since_iso=_extract_since(body),
        ))
    return out


def latest_patch_for_client(path: str, client_id: str) -> Optional[PatchEntry]:
    entries = read_patch_queue(path)
    # filter by extracted client_id; if missing, ignore
    hits = [e for e in entries if (e.client_id or "").lower() == client_id.lower()]
    return hits[-1] if hits else None
