from __future__ import annotations
"""Minimal MCP-style server (stdio) to enforce the project development model.

Dependency-light: JSON messages over stdin/stdout.

Methods:
- ops.run_tests
- ops.run_cli (whitelisted)
- horizon.append_entry (append markdown to a file)
- cadence.next_patch_id
- cadence.start_work
- cadence.finish_work
- cadence.create_patch
- cadence.verify_release

Wire into Cursor as an MCP server command:
  python -m ae.mcp_server --repo /path/to/repo --log-horizon-md /path/to/LOG_HORIZON.md
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

WHITELISTED_CLI = {
    "init-db",
    "validate-page",
    "publish-page",
    "pause-page",
    "enqueue-work",
    "list-work",
    "record-event",
    "enqueue-bulk",
    "run-bulk",
    "log-change",
}

def _send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

def _err(id_, code: str, message: str) -> dict:
    return {"id": id_, "error": {"code": code, "message": message}}

def _ok(id_, result: dict) -> dict:
    return {"id": id_, "result": result}

def append_to_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write("\n" + text.rstrip() + "\n")

def run_tests(repo_path: Path) -> dict:
    p = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=str(repo_path), capture_output=True, text=True)
    return {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}

def run_cli(repo_path: Path, args: list[str]) -> dict:
    if not args:
        return {"returncode": 2, "stderr": "No CLI args provided", "stdout": ""}
    cmd = args[0]
    if cmd not in WHITELISTED_CLI:
        return {"returncode": 2, "stderr": f"CLI command not allowed: {cmd}", "stdout": ""}
    p = subprocess.run([sys.executable, "-m", "ae.cli", cmd, *args[1:]], cwd=str(repo_path), capture_output=True, text=True)
    return {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--log-horizon-md", required=False)
    ns = ap.parse_args()

    repo_path = Path(ns.repo).resolve()
    log_path = Path(ns.log_horizon_md).resolve() if ns.log_horizon_md else None

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            _send(_err(None, "bad_json", "Invalid JSON"))
            continue

        id_ = req.get("id")
        method = req.get("method")
        params = req.get("params", {}) or {}

        try:
            if method == "ops.run_tests":
                _send(_ok(id_, run_tests(repo_path)))
            elif method == "ops.run_cli":
                _send(_ok(id_, run_cli(repo_path, params.get("args", []))))
            elif method == "cadence.next_patch_id":
                from . import cadence
                pid = cadence.next_patch_id(repo_path, date_yyyymmdd=params.get("date"))
                _send(_ok(id_, {"patch_id": pid}))
            elif method == "cadence.start_work":
                from . import cadence
                meta = cadence.start_work(
                    repo_root=repo_path,
                    version=params.get("version"),
                    type_=params.get("type"),
                    summary=params.get("summary"),
                    patch_id=params.get("patch_id"),
                )
                _send(_ok(id_, {"patch": meta.__dict__}))
            elif method == "cadence.finish_work":
                from . import cadence
                if not log_path:
                    _send(_err(id_, "no_log_path", "log-horizon-md not configured"))
                    continue
                res = cadence.finish_work(
                    repo_root=repo_path,
                    patch_id=params.get("patch_id"),
                    log_horizon_md=log_path,
                    artifacts=params.get("artifacts", []) or [],
                    notes=params.get("notes"),
                    next_=params.get("next"),
                )
                _send(_ok(id_, res))

            elif method == "cadence.create_patch":
                from . import cadence
                meta = cadence.create_patch(
                    repo_root=repo_path,
                    patch_id=params.get("patch_id"),
                    version=params.get("version"),
                    type_=params.get("type"),
                    summary=params.get("summary"),
                )
                _send(_ok(id_, {"patch": meta.__dict__}))
            elif method == "cadence.verify_release":
                from . import cadence
                if not log_path:
                    _send(_err(id_, "no_log_path", "log-horizon-md not configured"))
                    continue
                res = cadence.verify_release(
                    repo_root=repo_path,
                    patch_id=params.get("patch_id"),
                    log_horizon_md=log_path,
                    artifacts=params.get("artifacts", []) or [],
                    notes=params.get("notes"),
                    next_=params.get("next"),
                )
                _send(_ok(id_, res))

            elif method == "horizon.append_entry":
                if not log_path:
                    _send(_err(id_, "no_log_path", "log-horizon-md not configured"))
                    continue
                md = params.get("markdown")
                if not md:
                    _send(_err(id_, "missing_param", "params.markdown required"))
                    continue
                append_to_markdown(log_path, md)
                _send(_ok(id_, {"appended": True, "path": str(log_path)}))
            else:
                _send(_err(id_, "unknown_method", f"Unknown method: {method}"))
        except Exception as e:
            _send(_err(id_, "exception", str(e)))

if __name__ == "__main__":
    main()
