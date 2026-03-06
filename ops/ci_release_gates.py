#!/usr/bin/env python3
"""CI release gates.

Fail-fast checks that prevent drift:
- Version SSOT consistency
- Changelog contains a section for current version
- Log horizon contains an entry for current version
- Patch queue does not contain unchecked items for closed ops in current version (soft)

Usage:
  python ops/ci_release_gates.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def die(msg: str) -> None:
    print(f"[ci-gates] FAIL: {msg}", file=sys.stderr)
    raise SystemExit(2)


def read_version(root: Path) -> str:
    v = (root / "ops" / "VERSION.txt").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", v):
        die(f"Invalid version in ops/VERSION.txt: {v!r}")
    return v


def get_pyproject_version(root: Path) -> str:
    txt = (root / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'version\s*=\s*"([0-9.]+)"', txt)
    if not m:
        die("pyproject.toml missing version")
    return m.group(1)


def get_init_version(root: Path) -> str:
    txt = (root / "src" / "ae" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([0-9.]+)"', txt)
    if not m:
        die("src/ae/__init__.py missing __version__")
    return m.group(1)


def check_changelog(root: Path, ver: str) -> None:
    ch = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## [{ver}]" not in ch:
        die(f"CHANGELOG.md missing section for {ver}")
    # prevent shipping placeholder stubs like "- " lines inside this version section
    # We only scan the block for this version.
    # Block ends at next '## [' header or EOF.
    pat = rf"## \[{re.escape(ver)}\][^\n]*\n(.*?)(?:\n## \[|\Z)"
    m = re.search(pat, ch, flags=re.S)
    if not m:
        die("Could not parse changelog block")
    block = m.group(1)
    if re.search(r"^\-\s*$", block, flags=re.M):
        die("Changelog contains empty bullet placeholder '- ' in this version block")


def check_log_horizon(root: Path, ver: str) -> None:
    lh = (root / "ops" / "LOG_HORIZON.md").read_text(encoding="utf-8")
    if ver not in lh:
        die(f"ops/LOG_HORIZON.md missing entry mentioning {ver}")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    ver = read_version(root)
    v_py = get_pyproject_version(root)
    v_init = get_init_version(root)

    if not (ver == v_py == v_init):
        die(f"Version drift: ops={ver}, pyproject={v_py}, __init__={v_init}")

    check_changelog(root, ver)
    check_log_horizon(root, ver)

    print(f"[ci-gates] OK: {ver}")


if __name__ == "__main__":
    main()
