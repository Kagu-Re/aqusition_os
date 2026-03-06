import json
from pathlib import Path
from typer.testing import CliRunner

from ae.cli import app


def test_backfill_client_ids(tmp_path):
    workq = tmp_path / "WORK_QUEUE.md"
    patchq = tmp_path / "PATCH_QUEUE.md"

    workq.write_text(
        "## Work Queue\n\n"
        "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| W-AP-aaaaaaaaaa | AP-aaaaaaaaaa |  | open | rm | 2026-01-01T00:00:00Z |  |  | T1 |  |\n"
        "| W-AP-bbbbbbbbbb | AP-bbbbbbbbbb | c2 | open | rm | 2026-01-01T00:00:00Z |  |  | T2 |  |\n",
        encoding="utf-8",
    )

    patchq.write_text(
        "## Patch Queue\n\n"
        "## AP-aaaaaaaaaa\n"
        "- client_id: c1\n"
        "- platform: meta\n\n"
        "## AP-bbbbbbbbbb\n"
        "- client_id: c2\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    r = runner.invoke(app, ["work-backfill-client-ids", "--work-queue-path", str(workq), "--patch-queue-path", str(patchq), "--as-json"])
    assert r.exit_code == 0, r.stdout
    rep = json.loads(r.stdout)
    assert rep["updated"] == 1

    txt = workq.read_text(encoding="utf-8")
    assert "| W-AP-aaaaaaaaaa | AP-aaaaaaaaaa | c1 |" in txt
