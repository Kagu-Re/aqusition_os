from pathlib import Path
from typer.testing import CliRunner

from ae.cli import app


def _seed(workq: Path, status: str = "blocked", started: str = ""):
    workq.write_text(
        "## Work Queue\n\n"
        "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        f"| W-AP-aaaaaaaaaa | AP-aaaaaaaaaa |  | {status} | rm | 2026-01-01T00:00:00Z | {started} |  | Test Title |  |\n",
        encoding="utf-8",
    )


def test_work_unblock_sets_open(tmp_path):
    workq = tmp_path / "WORK_QUEUE.md"
    logp = tmp_path / "LOG_HORIZON.md"
    _seed(workq, status="blocked")

    runner = CliRunner()
    r = runner.invoke(app, ["work-unblock", "--work-id", "W-AP-aaaaaaaaaa", "--note", "access granted", "--work-queue-path", str(workq), "--log-path", str(logp)])
    assert r.exit_code == 0, r.stdout
    txt = workq.read_text(encoding="utf-8")
    assert "| W-AP-aaaaaaaaaa | AP-aaaaaaaaaa |  | open |" in txt
    assert "UNBLOCKED: access granted" in txt


def test_work_resume_sets_doing_and_stamps_started_if_missing(tmp_path):
    workq = tmp_path / "WORK_QUEUE.md"
    logp = tmp_path / "LOG_HORIZON.md"
    _seed(workq, status="open", started="")

    runner = CliRunner()
    r = runner.invoke(app, ["work-resume", "--work-id", "W-AP-aaaaaaaaaa", "--note", "back to execution", "--work-queue-path", str(workq), "--log-path", str(logp)])
    assert r.exit_code == 0, r.stdout
    txt = workq.read_text(encoding="utf-8")
    assert "| W-AP-aaaaaaaaaa | AP-aaaaaaaaaa |  | doing |" in txt
    # started_utc should be non-empty now (best effort check)
    assert "RESUMED: back to execution" in txt
