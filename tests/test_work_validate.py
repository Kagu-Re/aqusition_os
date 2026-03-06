import json
from pathlib import Path
from typer.testing import CliRunner
from ae.cli import app


def test_work_validate_reports_missing_client_id(tmp_path):
    workq = tmp_path / "WORK_QUEUE.md"
    workq.write_text(
        "## Work Queue\n\n"
        "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| W-AP-aaaaaaaaaa | AP-aaaaaaaaaa |  | open | rm | 2026-01-01T00:00:00Z |  |  | T1 |  |\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    r = runner.invoke(app, ["work-validate", "--work-queue-path", str(workq), "--as-json", "--stale-days", "0"])
    assert r.exit_code == 0
    rep = json.loads(r.stdout)
    assert rep["missing_client_id"] == 1
