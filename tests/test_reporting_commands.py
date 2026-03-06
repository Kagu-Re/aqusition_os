import json
from pathlib import Path
from typer.testing import CliRunner

from ae.cli import app


def _seed(workq: Path):
    workq.write_text(
        "## Work Queue\n\n"
        "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| W-AP-1 | AP-1 |  | done | rm | 2026-01-01T00:00:00Z | 2026-01-01T01:00:00Z | 2026-01-03T00:00:00Z | T1 | shipped |\n"
        "| W-AP-2 | AP-2 |  | blocked | rm | 2026-01-02T00:00:00Z |  |  | T2 | BLOCKED: waiting on access |\n"
        "| W-AP-3 | AP-3 |  | open | bot | 2026-01-03T00:00:00Z |  |  | Pixel setup | need pixel access |\n",
        encoding="utf-8",
    )


def test_work_search(tmp_path):
    workq = tmp_path / "WORK_QUEUE.md"
    _seed(workq)
    runner = CliRunner()
    r = runner.invoke(app, ["work-search", "--q", "pixel", "--work-queue-path", str(workq), "--as-json"])
    assert r.exit_code == 0, r.stdout
    arr = json.loads(r.stdout)
    assert len(arr) == 1
    assert arr[0]["work_id"] == "W-AP-3"


def test_ops_report_json(tmp_path):
    workq = tmp_path / "WORK_QUEUE.md"
    _seed(workq)
    runner = CliRunner()
    r = runner.invoke(app, ["ops-report", "--last", "3650", "--work-queue-path", str(workq), "--as-json"])
    assert r.exit_code == 0, r.stdout
    obj = json.loads(r.stdout)
    assert obj["window_total"] == 3
    assert obj["done"] == 1
    assert obj["blocked"] == 1
    assert obj["top_blocked_reasons"][0]["reason"] == "waiting on access"


def test_work_stale_json(tmp_path):
    workq = tmp_path / "WORK_QUEUE.md"
    _seed(workq)
    runner = CliRunner()
    # very small threshold so all show up
    r = runner.invoke(app, ["work-stale", "--days", "0", "--work-queue-path", str(workq), "--as-json"])
    assert r.exit_code == 0, r.stdout
    arr = json.loads(r.stdout)
    assert len(arr) >= 1
