import json
from pathlib import Path
from typer.testing import CliRunner

from ae.cli import app


def _seed(workq: Path):
    workq.write_text(
        "## Work Queue\n\n"
        "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| W-AP-1 | AP-1 |  | open | rm | 2026-01-01T00:00:00Z |  |  | T1 |  |\n"
        "| W-AP-2 | AP-2 |  | blocked | rm | 2026-01-02T00:00:00Z |  |  | T2 | BLOCKED: waiting on access |\n"
        "| W-AP-3 | AP-3 |  | done | bot | 2026-01-03T00:00:00Z | 2026-01-03T01:00:00Z | 2026-01-03T02:00:00Z | T3 | shipped |\n",
        encoding="utf-8",
    )


def test_work_list_filters_and_json(tmp_path):
    workq = tmp_path / "WORK_QUEUE.md"
    _seed(workq)
    runner = CliRunner()

    r1 = runner.invoke(app, ["work-list", "--status", "blocked", "--work-queue-path", str(workq), "--as-json"])
    assert r1.exit_code == 0, r1.stdout
    arr = json.loads(r1.stdout)
    assert len(arr) == 1
    assert arr[0]["work_id"] == "W-AP-2"

    r2 = runner.invoke(app, ["work-list", "--assignee", "rm", "--work-queue-path", str(workq), "--as-json"])
    assert r2.exit_code == 0, r2.stdout
    arr2 = json.loads(r2.stdout)
    assert len(arr2) == 2


def test_work_show_and_ops_status(tmp_path):
    workq = tmp_path / "WORK_QUEUE.md"
    patchq = tmp_path / "PATCH_QUEUE.md"
    logp = tmp_path / "LOG_HORIZON.md"
    _seed(workq)
    patchq.write_text("## Patch Queue\n", encoding="utf-8")
    logp.write_text("# Log Horizon\n", encoding="utf-8")

    runner = CliRunner()
    r1 = runner.invoke(app, ["work-show", "--work-id", "W-AP-3", "--work-queue-path", str(workq), "--as-json"])
    assert r1.exit_code == 0, r1.stdout
    obj = json.loads(r1.stdout)
    assert obj["status"] == "done"

    r2 = runner.invoke(app, ["ops-status", "--work-queue-path", str(workq), "--patch-queue-path", str(patchq), "--log-path", str(logp), "--as-json"])
    assert r2.exit_code == 0, r2.stdout
    s = json.loads(r2.stdout)
    assert s["work_total"] == 3
    assert s["status_counts"]["blocked"] == 1
    assert s["top_blocked_reasons"][0]["reason"] == "waiting on access"
