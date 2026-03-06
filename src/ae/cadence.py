from __future__ import annotations
"""Cadence enforcement utilities.

Goal: make it hard to ship changes without:
- patch metadata
- tests passing
- log horizon entry appended
- release record written

File-based, dependency-light.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json
import re
import subprocess
import sys
from typing import Optional, Tuple

PATCH_ID_RE = re.compile(r"^P-\d{8}-\d{4}$")

@dataclass(frozen=True)
class PatchMeta:
    patch_id: str
    version: str
    type: str
    summary: str
    created_at: str

def validate_patch_id(patch_id: str) -> None:
    if not patch_id or not PATCH_ID_RE.match(patch_id):
        raise ValueError(f"Invalid patch_id '{patch_id}'. Expected P-YYYYMMDD-####")

def ensure_dirs(repo_root: Path) -> Tuple[Path, Path]:
    patches_dir = repo_root / "ops" / "patches"
    releases_dir = repo_root / "ops" / "releases"
    patches_dir.mkdir(parents=True, exist_ok=True)
    releases_dir.mkdir(parents=True, exist_ok=True)
    return patches_dir, releases_dir

def patch_path(repo_root: Path, patch_id: str) -> Path:
    validate_patch_id(patch_id)
    patches_dir, _ = ensure_dirs(repo_root)
    return patches_dir / f"{patch_id}.json"

def release_path(repo_root: Path, patch_id: str) -> Path:
    validate_patch_id(patch_id)
    _, releases_dir = ensure_dirs(repo_root)
    return releases_dir / f"{patch_id}.json"

def create_patch(repo_root: Path, patch_id: str, version: str, type_: str, summary: str) -> PatchMeta:
    validate_patch_id(patch_id)
    p = patch_path(repo_root, patch_id)
    if p.exists():
        raise FileExistsError(f"Patch already exists: {p}")
    meta = PatchMeta(
        patch_id=patch_id,
        version=version,
        type=type_,
        summary=summary,
        created_at=datetime.utcnow().isoformat(),
    )
    p.write_text(json.dumps(meta.__dict__, indent=2), encoding="utf-8")
    return meta

def load_patch(repo_root: Path, patch_id: str) -> PatchMeta:
    p = patch_path(repo_root, patch_id)
    data = json.loads(p.read_text(encoding="utf-8"))
    return PatchMeta(**data)

def run_tests(repo_root: Path) -> dict:
    p = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=str(repo_root), capture_output=True, text=True)
    return {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}

def append_log_entry(log_horizon_md: Path, entry_md: str) -> None:
    log_horizon_md.parent.mkdir(parents=True, exist_ok=True)
    with log_horizon_md.open("a", encoding="utf-8") as f:
        f.write("\n" + entry_md.rstrip() + "\n")

def generate_log_entry(meta: PatchMeta, tests: dict, artifacts: list[str], notes: Optional[str] = None, next_: Optional[str] = None) -> str:
    dt = datetime.utcnow().date().isoformat()
    lines: list[str] = []
    lines.append(f"**ID:** {meta.patch_id}  ")
    lines.append(f"**Date:** {dt}  ")
    lines.append(f"**Version:** {meta.version}  ")
    lines.append(f"**Type:** {meta.type}  ")
    lines.append("")
    lines.append("### Summary")
    lines.append(f"- {meta.summary}")
    lines.append("")
    lines.append("### Artifacts")
    if artifacts:
        for a in artifacts:
            lines.append(f"- {a}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("### Tests")
    if tests.get("returncode") == 0:
        out = (tests.get("stdout") or "").strip()
        lines.append(f"- pytest: PASS ({out})")
    else:
        lines.append("- pytest: FAIL")
    lines.append("")
    lines.append("### Notes / Insights")
    lines.append(f"- {notes or '(none)'}")
    lines.append("")
    lines.append("### Next")
    lines.append(f"- {next_ or '(none)'}")
    lines.append("")
    lines.append("---")
    return "\n".join(lines)



def next_patch_id(repo_root: Path, date_yyyymmdd: Optional[str] = None) -> str:
    """Return next patch id for a date based on existing ops/patches files.

    Example: if P-20260130-0003 exists, returns P-20260130-0004.
    """
    if date_yyyymmdd is None:
        date_yyyymmdd = datetime.utcnow().strftime("%Y%m%d")

    patches_dir, _ = ensure_dirs(repo_root)
    # scan existing patch files
    max_n = 0
    prefix = f"P-{date_yyyymmdd}-"
    for p in patches_dir.glob(f"P-{date_yyyymmdd}-*.json"):
        m = re.match(rf"^P-{date_yyyymmdd}-(\d{{4}})\.json$", p.name)
        if not m:
            continue
        n = int(m.group(1))
        max_n = max(max_n, n)
    return f"{prefix}{max_n+1:04d}"


def start_work(repo_root: Path, version: str, type_: str, summary: str, patch_id: Optional[str] = None) -> PatchMeta:
    """Create (or reuse) patch metadata for the current work unit."""
    if not patch_id:
        patch_id = next_patch_id(repo_root)
    return create_patch(repo_root, patch_id, version, type_, summary)


def finish_work(repo_root: Path, patch_id: str, log_horizon_md: Path, artifacts: list[str], notes: Optional[str], next_: Optional[str]) -> dict:
    """Verify and record release for an existing patch."""
    return verify_release(repo_root, patch_id, log_horizon_md, artifacts, notes, next_)


def verify_release(repo_root: Path, patch_id: str, log_horizon_md: Path, artifacts: list[str], notes: Optional[str], next_: Optional[str]) -> dict:
    meta = load_patch(repo_root, patch_id)
    tests = run_tests(repo_root)
    if tests["returncode"] != 0:
        return {"ok": False, "reason": "tests_failed", "tests": tests}

    entry = generate_log_entry(meta, tests, artifacts=artifacts, notes=notes, next_=next_)
    append_log_entry(log_horizon_md, entry)

    rel = release_path(repo_root, patch_id)
    rel.write_text(json.dumps({
        "patch_id": patch_id,
        "version": meta.version,
        "released_at": datetime.utcnow().isoformat(),
        "artifacts": artifacts,
        "tests": {"returncode": tests["returncode"], "stdout": tests["stdout"]},
        "log_horizon": str(log_horizon_md),
    }, indent=2), encoding="utf-8")

    return {"ok": True, "tests": tests, "release_record": str(rel), "log_appended": True}
