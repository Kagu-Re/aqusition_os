from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Iterable, List

from .workqueue import migrate_work_queue_schema


@dataclass(frozen=True)
class WorkRow:
    work_id: str
    patch_id: str
    client_id: str
    status: str
    assignee: str
    created_utc: str
    started_utc: str
    done_utc: str
    title: str
    notes: str


def _parse_md_table_rows(lines: Iterable[str]) -> List[WorkRow]:
    rows: List[WorkRow] = []
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        if line.startswith("|---"):
            continue
        # skip header row(s)
        if "work_id" in line and "patch_id" in line and "status" in line:
            continue

        cells = [c.strip() for c in line.strip("|").split("|")]

        # v2: 10 cols, v1: 9 cols (no client_id)
        if len(cells) == 9:
            # insert empty client_id after patch_id
            cells.insert(2, "")
        if len(cells) < 10:
            continue

        rows.append(WorkRow(
            work_id=cells[0],
            patch_id=cells[1],
            client_id=cells[2],
            status=cells[3],
            assignee=cells[4],
            created_utc=cells[5],
            started_utc=cells[6],
            done_utc=cells[7],
            title=cells[8],
            notes=cells[9],
        ))
    return rows


def read_work_queue(work_queue_path: str) -> List[WorkRow]:
    p = Path(work_queue_path)
    if not p.exists():
        return []
    # auto-migrate if needed
    migrate_work_queue_schema(str(p))
    lines = p.read_text(encoding="utf-8").splitlines()
    return _parse_md_table_rows(lines)


def find_work(work_queue_path: str, work_id: str) -> Optional[WorkRow]:
    for r in read_work_queue(work_queue_path):
        if r.work_id == work_id:
            return r
    return None


def filter_work(rows: List[WorkRow], *, status: Optional[str] = None, assignee: Optional[str] = None, client_id: Optional[str] = None) -> List[WorkRow]:
    out = rows
    if status:
        out = [r for r in out if r.status.lower() == status.lower()]
    if assignee:
        out = [r for r in out if r.assignee.lower() == assignee.lower()]
    if client_id:
        out = [r for r in out if r.client_id.lower() == client_id.lower()]
    return out
