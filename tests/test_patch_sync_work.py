from pathlib import Path
from typer.testing import CliRunner

from ae.cli import app


def test_patch_sync_work_updates_existing_rows(tmp_path: Path):
    workq = tmp_path / "WORK_QUEUE.md"
    workq.write_text(
        "## Work Queue\n\n"
        "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| W-1 | AP-1 | c1 | open | rm | 2026-01-01T00:00:00Z |  |  | A |  |\n"
        "| W-2 | AP-2 | c2 | doing | rm | 2026-01-01T00:00:00Z | 2026-01-01T00:00:00Z |  | B |  |\n",
        encoding="utf-8",
    )

    patchq = tmp_path / "PATCH_QUEUE.md"
    patchq.write_text(
        "## AP-1 — Fix A\n"
        "🟨 in-progress\n\n"
        "**Generated:** 2026-01-02T00:00:00Z\n"
        "**Source:** work_id=W-1 kind=open_sla_breach client_id=c1 age_days=20 threshold_days=14\n\n"
        "---\n\n"
        "## AP-2 — Fix B\n"
        "✅ done\n\n"
        "**Generated:** 2026-01-02T00:00:00Z\n"
        "**Source:** work_id=W-2 kind=doing_sla_breach client_id=c2 age_days=10 threshold_days=7\n\n"
        "---\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    res = runner.invoke(app, [
        "patch-sync-work",
        "--work-queue-path", str(workq),
        "--patch-queue-path", str(patchq),
    ])
    assert res.exit_code == 0, res.output

    txt = workq.read_text(encoding="utf-8")
    assert "| W-1 | AP-1 | c1 | doing |" in txt
    assert "| W-2 | AP-2 | c2 | done |" in txt


def test_reconcile_queues_runs_both_directions(tmp_path: Path):
    workq = tmp_path / "WORK_QUEUE.md"
    workq.write_text(
        "## Work Queue\n\n"
        "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| W-1 | AP-1 | c1 | doing | rm | 2026-01-01T00:00:00Z | 2026-01-01T00:00:00Z |  | A |  |\n",
        encoding="utf-8",
    )

    patchq = tmp_path / "PATCH_QUEUE.md"
    patchq.write_text(
        "## AP-1 — Fix A\n"
        "⬜ planned\n\n"
        "**Generated:** 2026-01-02T00:00:00Z\n"
        "**Source:** work_id=W-1 kind=open_sla_breach client_id=c1 age_days=20 threshold_days=14\n\n"
        "---\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    res = runner.invoke(app, [
        "reconcile-queues",
        "--work-queue-path", str(workq),
        "--patch-queue-path", str(patchq),
    ])
    assert res.exit_code == 0, res.output

    # after reconciliation, WORK_QUEUE doing should push PATCH_QUEUE to 🟨 in-progress
    ptxt = patchq.read_text(encoding="utf-8")
    assert "🟨 in-progress" in ptxt
