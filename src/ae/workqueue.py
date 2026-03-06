from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List


@dataclass(frozen=True)
class WorkItem:
    work_id: str
    patch_id: str
    client_id: str
    created_utc: str
    assignee: str
    status: str
    title: str
    link_hint: str
    started_utc: Optional[str] = None
    done_utc: Optional[str] = None
    notes: Optional[str] = None


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat() + "Z"


WORKQ_HEADER_V2 = (
    "## Work Queue\n\n"
    "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
    "|---|---|---|---|---|---|---|---|---|---|\n"
)

WORKQ_HEADER_V1 = (
    "## Work Queue\n\n"
    "| work_id | patch_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
    "|---|---|---|---|---|---|---|---|---|\n"
)



def parse_work_queue(work_queue_path: str) -> List[WorkItem]:
    """Parse WORK_QUEUE.md into WorkItem objects (v2 schema enforced).

    Missing optional columns are tolerated via migration.
    """
    p = Path(work_queue_path)
    if not p.exists():
        return []

    migrate_work_queue_schema(work_queue_path)
    lines = p.read_text(encoding="utf-8").splitlines()

    items: List[WorkItem] = []
    for line in lines:
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 9:
            continue

        # v2: work_id, patch_id, client_id, status, assignee, created_utc, started_utc, done_utc, title, notes
        # notes may be missing in older rows; pad.
        while len(cells) < 10:
            cells.append("")

        work_id, patch_id, client_id, status, assignee, created_utc, started_utc, done_utc, title, notes = cells[:10]
        if work_id.strip().lower() == "work_id":
            continue
        started_utc = started_utc or None
        done_utc = done_utc or None
        notes = notes or None

        items.append(
            WorkItem(
                work_id=work_id,
                patch_id=patch_id,
                client_id=client_id,
                created_utc=created_utc,
                assignee=assignee,
                status=status,
                title=title,
                link_hint="",
                started_utc=started_utc,
                done_utc=done_utc,
                notes=notes,
            )
        )

    return items
def make_work_item(*, patch_id: str, client_id: str, title: str, assignee: str, status: str = "open") -> WorkItem:
    now = _now()
    work_id = f"W-{patch_id}"
    link_hint = f"origin_patch_id={patch_id}"
    return WorkItem(
        work_id=work_id,
        patch_id=patch_id,
        client_id=client_id or "",
        created_utc=now,
        assignee=assignee,
        status=status,
        title=title,
        link_hint=link_hint,
    )


def _ensure_file(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(WORKQ_HEADER_V2, encoding="utf-8")
        return
    # if exists, migrate if needed
    migrate_work_queue_schema(str(p))


def migrate_work_queue_schema(work_queue_path: str) -> bool:
    """Upgrade WORK_QUEUE.md from v1 schema (no client_id col) to v2 schema.

    Safe migration: inserts empty client_id for existing rows.
    Returns True if migration happened.
    """
    p = Path(work_queue_path)
    if not p.exists():
        return False
    txt = p.read_text(encoding="utf-8")
    if "| work_id | patch_id | client_id |" in txt:
        return False  # already v2
    if "| work_id | patch_id | status |" not in txt:
        return False  # unknown format

    lines = txt.splitlines()
    out_lines: List[str] = []
    migrated = False
    for line in lines:
        if line.strip() == WORKQ_HEADER_V1.splitlines()[1].strip():
            # header row
            out_lines.append("| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |")
            migrated = True
            continue
        if line.strip() == WORKQ_HEADER_V1.splitlines()[2].strip():
            out_lines.append("|---|---|---|---|---|---|---|---|---|---|")
            migrated = True
            continue
        if line.startswith("|") and "work_id" not in line and not line.startswith("|---"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            # v1 expects 9 cells
            if len(cells) == 9:
                # insert empty client_id after patch_id
                cells.insert(2, "")
                out_lines.append("| " + " | ".join(cells) + " |")
                migrated = True
                continue
        out_lines.append(line)

    if migrated:
        p.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return migrated


def append_work_queue(work_queue_path: str, item: WorkItem) -> None:
    p = Path(work_queue_path)
    _ensure_file(p)

    txt = p.read_text(encoding="utf-8")
    if item.work_id in txt:
        return  # dedup

    row = (
        f"| {item.work_id} | {item.patch_id} | {item.client_id} | {item.status} | {item.assignee} | {item.created_utc} | "
        f"{item.started_utc or ''} | {item.done_utc or ''} | {item.title} | {item.notes or ''} |\n"
    )
    with p.open("a", encoding="utf-8") as f:
        f.write(row)


def _parse_table_lines(txt: str) -> List[str]:
    lines = txt.splitlines()
    return lines


def update_work_item(
    work_queue_path: str,
    work_id: str,
    *,
    status: Optional[str] = None,
    started_utc: Optional[str] = None,
    done_utc: Optional[str] = None,
    notes: Optional[str] = None,
    assignee: Optional[str] = None,
    client_id: Optional[str] = None,
) -> bool:
    """Update a work item row in WORK_QUEUE.md. Returns True if updated, False if not found."""
    p = Path(work_queue_path)
    if not p.exists():
        return False

    # ensure schema before editing
    migrate_work_queue_schema(work_queue_path)

    lines = p.read_text(encoding="utf-8").splitlines()
    new_lines = []
    updated = False

    for line in lines:
        if line.startswith("|") and f"| {work_id} |" in line:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            # Expected v2 columns:
            # work_id, patch_id, client_id, status, assignee, created_utc, started_utc, done_utc, title, notes
            if len(cells) < 10:
                new_lines.append(line)
                continue
            if client_id is not None:
                cells[2] = client_id
            if status is not None:
                cells[3] = status
            if assignee is not None:
                cells[4] = assignee
            if started_utc is not None:
                cells[6] = started_utc
            if done_utc is not None:
                cells[7] = done_utc
            if notes is not None:
                cells[9] = notes
            newline = "| " + " | ".join(cells) + " |"
            new_lines.append(newline)
            updated = True
        else:
            new_lines.append(line)

    if updated:
        p.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return updated


def start_work(work_queue_path: str, work_id: str) -> bool:
    return update_work_item(work_queue_path, work_id, status="doing", started_utc=_now())


def note_work(work_queue_path: str, work_id: str, note: str) -> bool:
    """Append (or set) notes field; keeps current status."""
    p = Path(work_queue_path)
    if not p.exists():
        return False
    migrate_work_queue_schema(work_queue_path)
    lines = p.read_text(encoding="utf-8").splitlines()
    for line in lines:
        if line.startswith("|") and f"| {work_id} |" in line:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 10:
                return False
            existing = cells[9].strip()
            merged = note if not existing else (existing + " ; " + note)
            return update_work_item(work_queue_path, work_id, notes=merged)
    return False


def block_work(work_queue_path: str, work_id: str, reason: str) -> bool:
    """Set status=blocked and add reason to notes."""
    ok = note_work(work_queue_path, work_id, f"BLOCKED: {reason}")
    if not ok:
        return False
    return update_work_item(work_queue_path, work_id, status="blocked")


def unblock_work(work_queue_path: str, work_id: str, note: str = "") -> bool:
    """Remove blocked status by setting status=open and optionally append note."""
    if note:
        ok = note_work(work_queue_path, work_id, f"UNBLOCKED: {note}")
        if not ok:
            return False
    return update_work_item(work_queue_path, work_id, status="open")


def resume_work(work_queue_path: str, work_id: str, note: str = "") -> bool:
    """Set status=doing. If started_utc missing, stamp it. Optionally append note."""
    if note:
        ok = note_work(work_queue_path, work_id, f"RESUMED: {note}")
        if not ok:
            return False

    p = Path(work_queue_path)
    if not p.exists():
        return False

    migrate_work_queue_schema(work_queue_path)

    lines = p.read_text(encoding="utf-8").splitlines()
    started_val = None
    for line in lines:
        if line.startswith("|") and f"| {work_id} |" in line:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 10:
                return False
            started_val = cells[6].strip()
            break
    if started_val is None:
        return False

    if started_val == "":
        return update_work_item(work_queue_path, work_id, status="doing", started_utc=_now())
    return update_work_item(work_queue_path, work_id, status="doing")


def complete_work(work_queue_path: str, work_id: str, notes: str = "") -> bool:
    return update_work_item(work_queue_path, work_id, status="done", done_utc=_now(), notes=notes)


def append_log_horizon(log_path: str, message: str) -> None:
    p = Path(log_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    stamp = _now()
    entry = f"\n## {stamp}\n{message.strip()}\n"
    if not p.exists():
        p.write_text("# Log Horizon\n", encoding="utf-8")
    with p.open("a", encoding="utf-8") as f:
        f.write(entry)


def backfill_client_ids(work_queue_path: str, patch_queue_path: str) -> dict:
    """Backfill missing client_id values in WORK_QUEUE using PATCH_QUEUE.

    Strategy:
    - Read PATCH_QUEUE and build patch_id -> client_id mapping (from `client_id:` field).
    - For each WORK_QUEUE row with empty client_id, if mapping exists for its patch_id, set client_id.
    Returns a small report dict.
    """
    from .patchqueue_reader import read_patch_queue

    p_wq = Path(work_queue_path)
    if not p_wq.exists():
        return {"updated": 0, "scanned": 0, "missing_after": 0}

    migrate_work_queue_schema(work_queue_path)

    entries = read_patch_queue(patch_queue_path)
    mapping = {}
    for e in entries:
        if e.client_id:
            mapping[e.patch_id] = e.client_id

    lines = p_wq.read_text(encoding="utf-8").splitlines()
    out_lines = []
    updated = 0
    scanned = 0
    missing_after = 0

    for line in lines:
        if line.startswith("|") and "work_id" not in line and not line.startswith("|---"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 9:
                cells.insert(2, "")
            if len(cells) >= 10:
                scanned += 1
                patch_id = cells[1]
                client_id = cells[2]
                if client_id == "" and patch_id in mapping:
                    cells[2] = mapping[patch_id]
                    updated += 1
                if cells[2] == "":
                    missing_after += 1
                out_lines.append("| " + " | ".join(cells[:10]) + " |")
                continue
        out_lines.append(line)

    if updated:
        p_wq.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    return {"updated": updated, "scanned": scanned, "missing_after": missing_after}


def set_work_status(path: str, patch_id: str, new_status: str) -> bool:
    """Update status of WORK_QUEUE row by patch_id.

    Returns True if file changed.
    """
    p = Path(path)
    if not p.exists():
        return False

    lines = p.read_text(encoding="utf-8").splitlines()

    header_idx = None
    for i,l in enumerate(lines):
        if l.startswith("| work_id"):
            header_idx = i
            break

    if header_idx is None:
        return False

    changed = False
    for i in range(header_idx+2, len(lines)):
        if not lines[i].startswith("|"):
            continue
        cols = [c.strip() for c in lines[i].strip("|").split("|")]
        if len(cols) < 4:
            continue

        pid = cols[1]
        if pid == patch_id:
            if cols[3] != new_status:
                cols[3] = new_status
                lines[i] = "| " + " | ".join(cols) + " |"
                changed = True

    if changed:
        p.write_text("\n".join(lines).rstrip()+"\n", encoding="utf-8")
    return changed



def update_work_for_patch(
    work_queue_path: str,
    patch_id: str,
    *,
    status: Optional[str] = None,
    started_utc: Optional[str] = None,
    done_utc: Optional[str] = None,
    notes: Optional[str] = None,
) -> int:
    """Update all work rows that reference the given patch_id.

    Returns number of rows updated.
    """
    items = parse_work_queue(work_queue_path)
    updated = 0
    for it in items:
        if (it.patch_id or "").strip() != (patch_id or "").strip():
            continue

        # Derive timestamps if caller didn't supply
        s = status.lower().strip() if status else None
        st = started_utc
        dn = done_utc

        if s == "doing" and st is None:
            # set started if missing
            if not it.started_utc:
                st = _now()
        if s == "done" and dn is None:
            if not it.done_utc:
                dn = _now()
            if st is None and not it.started_utc:
                st = _now()

        if update_work_item(
            work_queue_path,
            it.work_id,
            status=status,
            started_utc=st,
            done_utc=dn,
            notes=notes,
        ):
            updated += 1
    return updated
