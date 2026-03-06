from pathlib import Path
from typer.testing import CliRunner

from ae.cli import app


def test_reconcile_report_detects_conflict_and_winner(tmp_path: Path):
    workq = tmp_path / "WORK_QUEUE.md"
    workq.write_text(
        "## Work Queue\n\n"
        "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| W-1 | P-1 | c1 | done | rm | 2026-01-01T00:00:00Z | 2026-01-01T00:00:00Z | 2026-01-02T00:00:00Z | A |  |\n",
        encoding="utf-8",
    )

    patchq = tmp_path / "PATCH_QUEUE.md"
    patchq.write_text(
        "## P-1 — A\n"
        "🟨 in-progress\n\n"
        "**Generated:** 2026-01-02T00:00:00Z\n"
        "**Source:** work_id=W-1 kind=x client_id=c1 age_days=1 threshold_days=1\n\n"
        "---\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    res = runner.invoke(app, [
        "reconcile-report",
        "--work-queue-path", str(workq),
        "--patch-queue-path", str(patchq),
        "--precedence", "highest",
    ])
    assert res.exit_code == 0, res.output
    out = res.output
    assert "| P-1 | done | doing | done |" in out


def test_reconcile_queues_writes_report(tmp_path: Path):
    workq = tmp_path / "WORK_QUEUE.md"
    workq.write_text(
        "## Work Queue\n\n"
        "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| W-1 | P-1 | c1 | doing | rm | 2026-01-01T00:00:00Z | 2026-01-01T00:00:00Z |  | A |  |\n",
        encoding="utf-8",
    )

    patchq = tmp_path / "PATCH_QUEUE.md"
    patchq.write_text(
        "## P-1 — A\n"
        "⬜ planned\n\n"
        "**Generated:** 2026-01-02T00:00:00Z\n"
        "**Source:** work_id=W-1 kind=x client_id=c1 age_days=1 threshold_days=1\n\n"
        "---\n",
        encoding="utf-8",
    )

    report = tmp_path / "RECONCILE_REPORT.md"

    runner = CliRunner()
    res = runner.invoke(app, [
        "reconcile-queues",
        "--work-queue-path", str(workq),
        "--patch-queue-path", str(patchq),
        "--report-path", str(report),
        "--precedence", "work",
    ])
    assert res.exit_code == 0, res.output
    assert report.exists()
    txt = report.read_text(encoding="utf-8")
    assert "Reconcile Report" in txt
