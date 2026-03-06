import json
from pathlib import Path
from typer.testing import CliRunner
from ae.cli import app


def test_work_fix_backfill_and_validate(tmp_path):
    workq = tmp_path / "WORK_QUEUE.md"
    patchq = tmp_path / "PATCH_QUEUE.md"

    workq.write_text(
        "## Work Queue\n\n"
        "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| W-AP-aaaaaaaaaa | AP-aaaaaaaaaa |  | blocked | rm | 2026-01-01T00:00:00Z |  |  | T1 |  |\n",
        encoding="utf-8",
    )

    patchq.write_text(
        "## Patch Queue\n\n"
        "## AP-aaaaaaaaaa\n"
        "- client_id: c1\n"
        "- platform: meta\n\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    r = runner.invoke(app, ["work-fix", "--work-queue-path", str(workq), "--patch-queue-path", str(patchq), "--as-json", "--stale-days", "0"])
    assert r.exit_code == 0, r.stdout + r.stderr
    rep = json.loads(r.stdout)

    assert rep["backfill"]["updated"] == 1
    assert rep["validate"]["missing_client_id"] == 0
    # blocked without reason should be flagged
    assert rep["validate"]["blocked_no_reason"] == 1
    assert any(a["issue"] == "blocked_no_reason" for a in rep["actionable"])
