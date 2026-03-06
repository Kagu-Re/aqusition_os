from pathlib import Path
from typer.testing import CliRunner

from ae.cli import app


def _seed_workq(workq: Path):
    workq.write_text(
        "## Work Queue\n\n"
        "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| W-AP-aaaaaaaaaa | AP-aaaaaaaaaa |  | open | rm | 2026-01-01T00:00:00Z |  |  | Test Title |  |\n",
        encoding="utf-8",
    )


def test_work_start_and_done_updates_and_logs(tmp_path):
    workq = tmp_path / "WORK_QUEUE.md"
    logp = tmp_path / "LOG_HORIZON.md"
    _seed_workq(workq)

    runner = CliRunner()
    r1 = runner.invoke(app, ["work-start", "--work-id", "W-AP-aaaaaaaaaa", "--work-queue-path", str(workq), "--log-path", str(logp)])
    assert r1.exit_code == 0, r1.stdout
    txt = workq.read_text(encoding="utf-8")
    assert "| W-AP-aaaaaaaaaa | AP-aaaaaaaaaa |  | doing |" in txt
    assert "Log Horizon" in logp.read_text(encoding="utf-8")

    r2 = runner.invoke(app, ["work-done", "--work-id", "W-AP-aaaaaaaaaa", "--notes", "shipped", "--work-queue-path", str(workq), "--log-path", str(logp)])
    assert r2.exit_code == 0, r2.stdout
    txt2 = workq.read_text(encoding="utf-8")
    assert "| W-AP-aaaaaaaaaa | AP-aaaaaaaaaa |  | done |" in txt2
    assert "shipped" in txt2
    logtxt = logp.read_text(encoding="utf-8")
    assert "work_done" in logtxt
    assert "shipped" in logtxt
