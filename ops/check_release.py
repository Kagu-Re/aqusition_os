#!/usr/bin/env python3
"""Release gates (CI-friendly).

Checks:
1) Version SSOT files match:
   - ops/VERSION.txt
   - pyproject.toml
   - src/ae/__init__.py
2) CHANGELOG.md contains a section for the current version:
   - '## [X.Y.Z] - YYYY-MM-DD'
3) The version section is not an empty stub (needs at least 1 meaningful bullet).

Usage:
  python ops/check_release.py
  python ops/check_release.py --ci
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path


def die(msg: str) -> None:
    print(f"[release-gate] FAIL: {msg}", file=sys.stderr)
    raise SystemExit(2)


def ok(msg: str) -> None:
    print(f"[release-gate] OK: {msg}")


def read_version(root: Path) -> str:
    return (root / "ops" / "VERSION.txt").read_text(encoding="utf-8").strip()


def read_pyproject_version(root: Path) -> str:
    txt = (root / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'version\s*=\s*"([0-9.]+)"', txt)
    if not m:
        die("pyproject.toml missing version")
    return m.group(1)


def read_init_version(root: Path) -> str:
    txt = (root / "src" / "ae" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([0-9.]+)"', txt)
    if not m:
        die("src/ae/__init__.py missing __version__")
    return m.group(1)


def check_ssot(root: Path) -> str:
    v_ops = read_version(root)
    v_py = read_pyproject_version(root)
    v_init = read_init_version(root)
    if not (v_ops == v_py == v_init):
        die(f"version SSOT mismatch: ops={v_ops} pyproject={v_py} init={v_init}")
    ok(f"version SSOT match ({v_ops})")
    return v_ops


def extract_changelog_section(changelog: str, version: str) -> tuple[str, str]:
    pattern = re.compile(rf"^## \[{re.escape(version)}\] - (\d{{4}}-\d{{2}}-\d{{2}})\s*$", re.M)
    m = pattern.search(changelog)
    if not m:
        die(f"CHANGELOG.md missing section for {version}")
    date = m.group(1)

    start = m.end()
    m2 = re.search(r"^## \[", changelog[start:], flags=re.M)
    end = start + (m2.start() if m2 else len(changelog[start:]))
    body = changelog[start:end].strip()
    return date, body


def check_changelog(root: Path, version: str) -> None:
    p = root / "CHANGELOG.md"
    if not p.exists():
        die("CHANGELOG.md missing")
    txt = p.read_text(encoding="utf-8")

    date, body = extract_changelog_section(txt, version)

    # regex already validated date format; basic sanity:
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        die(f"CHANGELOG date invalid for {version}: {date}")

    ok(f"CHANGELOG has {version} section dated {date}")

    bullets = [ln.strip() for ln in body.splitlines() if ln.strip().startswith("-")]
    meaningful = [b for b in bullets if b not in ("-","- ", "- •") and len(b) > 3 and b != "-"]
    if not meaningful:
        die(f"CHANGELOG {version} section looks empty (no meaningful bullets)")
    ok("CHANGELOG entry has meaningful bullet(s)")



def check_artifact(root: Path, version: str) -> None:
    """Enforce: artifact exists OR documented skip reason.

    Priority:
    1) If ops/release_meta.json exists, use it.
    2) Else: require artifact file `acq_engine_vX_Y_Z.zip` at repo root.
    """
    meta_path = root / "ops" / "release_meta.json"
    default_name = f"acq_engine_v{version.replace('.', '_')}.zip"

    if meta_path.exists():
        try:
            meta = __import__("json").loads(meta_path.read_text(encoding="utf-8"))
            env = str(meta.get("env", "dev")).strip().lower() or "dev"
            if env not in ("dev", "prod"):
                die("release_meta.json env must be 'dev' or 'prod'")
        except Exception as e:
            die(f"release_meta.json invalid JSON: {e}")

        mv = str(meta.get("version", "")).strip()
        if mv and mv != version:
            die(f"release_meta.json version mismatch: meta={mv} current={version}")

        art = meta.get("artifact", {})
        mode = str(art.get("mode", "")).strip()
        filename = str(art.get("filename", default_name)).strip() or default_name
        reason = str(art.get("reason", "")).strip()

        if mode not in ("file", "skip"):
            die("release_meta.json artifact.mode must be 'file' or 'skip'")

        if env == "prod" and mode == "skip":
            die("artifact mode cannot be 'skip' when env is 'prod'")

        if mode == "skip":
            if len(reason) < 10:
                die("artifact mode is 'skip' but reason is missing/too short (>=10 chars)")
            ok("artifact check skipped with documented reason")
            return

        # mode == file
        p = root / filename
        if not p.exists():
            die(f"artifact file missing: {filename}")
        ok(f"artifact file present ({filename})")
        return

    # No meta file → strict default
    p = root / default_name
    if not p.exists():
        die(f"artifact file missing (default): {default_name} (or create ops/release_meta.json to skip)")
    ok(f"artifact file present ({default_name})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ci", action="store_true", help="CI-friendly output (same checks)")
    _ = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    version = check_ssot(root)
    check_changelog(root, version)
    check_artifact(root, version)
    print("[release-gate] PASS")


if __name__ == "__main__":
    main()
