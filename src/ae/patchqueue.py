from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import re


# -----------------------------
# Backward-compatible API (used by existing CLI + tests)
# -----------------------------

@dataclass(frozen=True)
class PatchEntry:
    patch_id: str
    title_line: str          # header line (e.g. "## AP-xxxxxxxxxx (timestamp) — ...")
    section_md: str          # full section markdown text


_HDR_RE_SIMPLE = re.compile(r"^##\s+(?P<id>[A-Za-z0-9_-]+)(?P<rest>.*)$")


def list_patch_ids(path: str) -> List[str]:
    """List patch ids from PATCH_QUEUE.md.

    We collect:
    - header ids from lines like `## AP-...`
    - body ids from lines like `- patch_id: `AP-...``
    """
    p = Path(path)
    if not p.exists():
        return []
    pat = re.compile(r"\-\s*patch_id:\s*`(?P<pid>[^`]+)`")
    hdr = re.compile(r"^##\s+(?P<pid>AP-[A-Za-z0-9_-]+)(\s+|$)")
    ids: List[str] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        hm = hdr.match(line.strip())
        if hm:
            pid = hm.group("pid").strip()
            if pid and pid not in ids:
                ids.append(pid)
        m = pat.search(line)
        if m:
            pid = m.group("pid").strip()
            if pid and pid not in ids:
                ids.append(pid)
    return ids


def find_patch_entry(path: str, patch_id: str) -> Optional[PatchEntry]:
    """Find a patch section for the given patch_id.

    Sections are delimited by markdown H2 headers (`## ...`).

    Match strategy:
    1) Header-based: if the header is exactly `## <patch_id>` or starts with `## <patch_id> `.
    2) Body-based: if the section contains `- patch_id: `<patch_id>``.
    """
    p = Path(path)
    if not p.exists():
        return None

    lines = p.read_text(encoding="utf-8").splitlines()

    hdr_idx = [i for i, l in enumerate(lines) if l.strip().startswith("## ")]
    hdr_idx.append(len(lines))

    hdr_pat = re.compile(rf"^##\s+{re.escape(patch_id)}(\s+|$)")
    pid_pat = re.compile(rf"\-\s*patch_id:\s*`{re.escape(patch_id)}`\s*$")

    for a, b in zip(hdr_idx, hdr_idx[1:]):
        section = lines[a:b]
        if not section:
            continue
        title_line = section[0].rstrip()
        if hdr_pat.match(title_line.strip()) or any(pid_pat.search(l) for l in section):
            section_md = "\n".join(section).strip() + "\n"
            return PatchEntry(patch_id=patch_id, title_line=title_line, section_md=section_md)

    return None

# -----------------------------
# New structured parsing API (for SLA utilities)
# -----------------------------

@dataclass(frozen=True)
class PatchQueueItem:
    patch_id: str
    title: str
    status: str              # raw status line (e.g. "⬜ planned", "✅ done")
    client_id: str
    work_id: str             # optional embedded work_id
    raw_block: str


_HDR_RE = re.compile(r"^##\s+(?P<id>\S+)\s+—\s+(?P<title>.+?)\s*$")
_STATUS_RE = re.compile(r"^(?P<status>[✅⬜🟨].+)$")
_SOURCE_RE = re.compile(
    r"\*\*Source:\*\*\s+.*?work_id=(?P<work_id>[^\s]+).*?kind=(?P<kind>[^\s]+).*?(?:client_id=(?P<client_id>[^\s]+))?",
    re.IGNORECASE,
)


def parse_patch_queue(path: str) -> List[PatchQueueItem]:
    """Parse PATCH_QUEUE.md into structured sections (best-effort)."""
    text = Path(path).read_text(encoding="utf-8") if Path(path).exists() else ""
    lines = text.splitlines()

    items: List[PatchQueueItem] = []
    i = 0
    while i < len(lines):
        m = _HDR_RE.match(lines[i].strip())
        if not m:
            i += 1
            continue

        patch_id = m.group("id").strip()
        title = m.group("title").strip()
        start = i
        i += 1

        status = ""
        client_id = ""
        work_id = ""

        if i < len(lines):
            sm = _STATUS_RE.match(lines[i].strip())
            if sm:
                status = sm.group("status").strip()
                i += 1

        block_lines = []
        while i < len(lines) and not _HDR_RE.match(lines[i].strip()):
            block_lines.append(lines[i])
            srcm = _SOURCE_RE.search(lines[i])
            if srcm:
                if srcm.groupdict().get("client_id"):
                    client_id = (srcm.group("client_id") or "").strip()
                work_id = (srcm.group("work_id") or "").strip()
            i += 1

        raw_block = "\n".join([lines[start]] + ([status] if status else []) + block_lines).strip() + "\n"
        items.append(
            PatchQueueItem(
                patch_id=patch_id,
                title=title,
                status=status,
                client_id=client_id,
                work_id=work_id,
                raw_block=raw_block,
            )
        )

    return items


def filter_items(items: List[PatchQueueItem], *, status_prefix: str = "⬜") -> List[PatchQueueItem]:
    return [x for x in items if (x.status or "").strip().startswith(status_prefix)]



def find_patch_span(path: str, patch_id: str) -> Optional[tuple[int, int]]:
    """Return (start_idx, end_idx) line indices for the patch section, or None."""
    p = Path(path)
    if not p.exists():
        return None

    lines = p.read_text(encoding="utf-8").splitlines()
    hdr_idx = [i for i, l in enumerate(lines) if l.strip().startswith("## ")]
    hdr_idx.append(len(lines))

    hdr_pat = re.compile(rf"^##\s+{re.escape(patch_id)}(\s+|$)")
    pid_pat = re.compile(rf"\-\s*patch_id:\s*`{re.escape(patch_id)}`\s*$")

    for a, b in zip(hdr_idx, hdr_idx[1:]):
        section = lines[a:b]
        if not section:
            continue
        title_line = section[0].rstrip()
        if hdr_pat.match(title_line.strip()) or any(pid_pat.search(l) for l in section):
            return (a, b)
    return None


def set_patch_status(path: str, patch_id: str, new_status_line: str) -> bool:
    """Set the status line (immediately after header) for a patch section.

    Returns True if file changed.
    """
    span = find_patch_span(path, patch_id)
    if not span:
        return False

    a, b = span
    p = Path(path)
    lines = p.read_text(encoding="utf-8").splitlines()

    # status line is conventionally the first non-empty line after header
    i = a + 1
    while i < b and lines[i].strip() == "":
        i += 1

    changed = False
    if i < b and _STATUS_RE.match(lines[i].strip()):
        if lines[i].strip() != new_status_line.strip():
            lines[i] = new_status_line.strip()
            changed = True
    else:
        # insert status line right after header + blank line if needed
        insert_at = a + 1
        lines.insert(insert_at, new_status_line.strip())
        changed = True

    if changed:
        p.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return changed
