"""Preflight gate check for CI/local ops checks.

Runs `ae preflight` using environment + profiles + policy files in ops/.
Exit code 0 => pass
Exit code 2 => gate fail
Other => error
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "ops" / "PREFLIGHT_POLICY.json"
ENV = ROOT / "ops" / "ENV.json"
PROFILES = ROOT / "ops" / "PREFLIGHT_PROFILES.json"

def main() -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")

    script = (
        "from ae.cli import app; "
        "from typer.main import get_command; "
        "import sys; "
        "cmd=get_command(app); "
        "sys.exit(cmd(['preflight',"
        "'--policy-path',str(%r),"
        "'--env-path',str(%r),"
        "'--profiles-path',str(%r)"
        "]))"
    ) % (str(POLICY), str(ENV), str(PROFILES))

    r = subprocess.run([sys.executable, "-c", script], cwd=str(ROOT), env=env)
    return r.returncode

if __name__ == "__main__":
    raise SystemExit(main())
