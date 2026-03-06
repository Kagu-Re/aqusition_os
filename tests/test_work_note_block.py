from pathlib import Path
from typer.testing import CliRunner

from ae.cli import app


def _seed(workq: Path):
    workq.write_text(
        "## Work Queue\n\n"
        "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| W-AP-aaaaaaaaaa | AP-aaaaaaaaaa |  | open | rm | 2026-01-01T00:00:00Z |  |  | Test Title |  |\n",
        encoding="utf-8",
    )


def test_work_note_and_block(tmp_path):
    workq = tmp_path / "WORK_QUEUE.md"
    logp = tmp_path / "LOG_HORIZON.md"
    _seed(workq)

    runner = CliRunner()
    r1 = runner.invoke(app, ["work-note", "--work-id", "W-AP-aaaaaaaaaa", "--note", "need pixel access", "--work-queue-path", str(workq), "--log-path", str(logp)])
    assert r1.exit_code == 0, r1.stdout
    txt = workq.read_text(encoding="utf-8")
    assert "need pixel access" in txt
    assert "| W-AP-aaaaaaaaaa | AP-aaaaaaaaaa |  | open |" in txt

    r2 = runner.invoke(app, ["work-block", "--work-id", "W-AP-aaaaaaaaaa", "--reason", "waiting on admin", "--work-queue-path", str(workq), "--log-path", str(logp)])
    assert r2.exit_code == 0, r2.stdout
    txt2 = workq.read_text(encoding="utf-8")
    assert "| W-AP-aaaaaaaaaa | AP-aaaaaaaaaa |  | blocked |" in txt2
    assert "BLOCKED: waiting on admin" in txt2
