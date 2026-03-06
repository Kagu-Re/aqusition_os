import json
from pathlib import Path
from typer.testing import CliRunner
from ae.cli import app


def test_patch_to_work_promotes_planned_sections(tmp_path):
    patchq = tmp_path / "PATCH_QUEUE.md"
    workq = tmp_path / "WORK_QUEUE.md"

    patchq.write_text(
        "# Patch Queue\n\n"
        "## Q-SLA-deadbeef — SLA: Example\n"
        "⬜ planned\n\n"
        "**Generated:** 2026-02-02T00:00:00Z\n"
        "**Source:** work_id=W-XYZ kind=open_sla_breach age_days=10 threshold_days=1 client_id=C1\n\n"
        "---\n\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    r = runner.invoke(app, ["patch-to-work", "--patch-queue-path", str(patchq), "--work-queue-path", str(workq), "--top-n", "5", "--assignee", "rm"])
    assert r.exit_code == 0
    txt = workq.read_text(encoding="utf-8")
    assert "| work_id | patch_id |" in txt
    assert "Q-SLA-deadbeef" in txt

    # idempotent second run
    r2 = runner.invoke(app, ["patch-to-work", "--patch-queue-path", str(patchq), "--work-queue-path", str(workq), "--top-n", "5", "--assignee", "rm"])
    assert r2.exit_code == 0
    txt2 = workq.read_text(encoding="utf-8")
    assert txt2.count("Q-SLA-deadbeef") == 1
