"""Local CI runner: validate-aliases + pytest.

Usage:
  python ops/checks/run_all.py
  python ops/checks/run_all.py --aliases-path cfg/aliases.json
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Ensure local src takes precedence
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def _run(cmd: list[str]) -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src") + (os.pathsep + env.get("PYTHONPATH") if env.get("PYTHONPATH") else "")
    p = subprocess.run(cmd, cwd=str(ROOT), env=env)
    return p.returncode

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aliases-path", default="ops/ad_platform_aliases.json")
    args = ap.parse_args()

    rc = _run([sys.executable, "-m", "ae.cli", "validate-aliases", "--aliases-path", args.aliases_path])
    if rc != 0:
        return rc

    rc = _run([sys.executable, "-m", "pytest", "-q"])
    return rc

if __name__ == "__main__":
    raise SystemExit(main())

# preflight gate
