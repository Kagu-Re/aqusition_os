#!/usr/bin/env python3
"""Release helper.

This script is intentionally small and boring.
It updates version SSOT files and appends a changelog stub.

Usage:
  python ops/release.py 3.1.0

Notes:
- It does NOT tag git or publish anything.
- It does NOT build the zip artifact (do that in your CI or manually).
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path


def die(msg: str) -> None:
    print(f"[release] ERROR: {msg}", file=sys.stderr)
    raise SystemExit(2)


def valid_ver(v: str) -> bool:
    return bool(re.fullmatch(r"\d+\.\d+\.\d+", v))


def write_version_files(root: Path, ver: str) -> None:
    (root / "ops/VERSION.txt").write_text(ver + "\n", encoding="utf-8")

    pyproj = root / "pyproject.toml"
    pt = pyproj.read_text(encoding="utf-8")
    pt2, n = re.subn(r'version\s*=\s*"[0-9.]+"', f'version = "{ver}"', pt, count=1)
    if n != 1:
        die("Could not update pyproject.toml version")
    pyproj.write_text(pt2, encoding="utf-8")

    initp = root / "src/ae/__init__.py"
    it = initp.read_text(encoding="utf-8")
    it2, n2 = re.subn(r'__version__\s*=\s*"[0-9.]+"', f'__version__ = "{ver}"', it, count=1)
    if n2 != 1:
        die("Could not update src/ae/__init__.py __version__")
    initp.write_text(it2, encoding="utf-8")


def append_changelog_stub(root: Path, ver: str) -> None:
    ch = root / "CHANGELOG.md"
    if not ch.exists():
        die("CHANGELOG.md not found")

    txt = ch.read_text(encoding="utf-8").splitlines()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    stub = [
        f"## [{ver}] - {today}",
        "### Added",
        "- ",
        "### Changed",
        "- ",
        "### Fixed",
        "- ",
        "",
    ]

    # Insert stub right after [Unreleased] header.
    out = []
    inserted = False
    i = 0
    while i < len(txt):
        out.append(txt[i])
        if txt[i].strip() == "## [Unreleased]" and not inserted:
            out.append("")
            out.extend(stub)
            inserted = True
        i += 1

    if not inserted:
        die("Could not find '## [Unreleased]' in CHANGELOG.md")

    ch.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        die("Usage: python ops/release.py X.Y.Z")
    ver = sys.argv[1].strip()
    if not valid_ver(ver):
        die("Version must be X.Y.Z (SemVer)")

    root = Path(__file__).resolve().parents[1]
    write_version_files(root, ver)
    append_changelog_stub(root, ver)
    print(f"[release] updated version to {ver} and appended changelog stub")


if __name__ == "__main__":
    main()
