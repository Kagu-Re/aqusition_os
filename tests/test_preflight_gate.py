from pathlib import Path
from typer.testing import CliRunner
from ae.cli import app


def test_preflight_exits_nonzero_when_actionable(tmp_path):
    workq = tmp_path / "WORK_QUEUE.md"
    patchq = tmp_path / "PATCH_QUEUE.md"

    workq.write_text(
        "## Work Queue\n\n"
        "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| W-AP-aaaaaaaaaa | AP-aaaaaaaaaa |  | open | rm | 2026-01-01T00:00:00Z |  |  | T1 |  |\n",
        encoding="utf-8",
    )
    patchq.write_text(
        "## Patch Queue\n\n"
        "## AP-aaaaaaaaaa\n"
        "- platform: meta\n\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    r = runner.invoke(app, ["preflight", "--work-queue-path", str(workq), "--patch-queue-path", str(patchq), "--max-actionable", "0"])
    assert r.exit_code == 2
