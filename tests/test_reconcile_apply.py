from pathlib import Path
from typer.testing import CliRunner

from ae.cli import app


def test_reconcile_apply_promotes_states(tmp_path: Path):
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
        "**Source:** work_id=W-1 kind=x client_id=c1\n\n"
        "---\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    res = runner.invoke(app, [
        "reconcile-apply",
        "--work-queue-path", str(workq),
        "--patch-queue-path", str(patchq),
        "--precedence", "highest",
    ])
    assert res.exit_code == 0, res.output

    ptxt = patchq.read_text(encoding="utf-8")
    assert "🟨 in-progress" in ptxt  # patch promoted to doing


def test_reconcile_apply_blocks_downgrade_by_default(tmp_path: Path):
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
        "**Source:** work_id=W-1 kind=x client_id=c1\n\n"
        "---\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    # precedence=patch would choose doing, but should be skipped as downgrade (work is done)
    res = runner.invoke(app, [
        "reconcile-apply",
        "--work-queue-path", str(workq),
        "--patch-queue-path", str(patchq),
        "--precedence", "patch",
    ])
    assert res.exit_code == 0, res.output

    # should remain done in work and patch should stay in-progress (no forced change)
    wtxt = workq.read_text(encoding="utf-8")
    assert "| W-1 | P-1 | c1 | done |" in wtxt
    ptxt = patchq.read_text(encoding="utf-8")
    assert "🟨 in-progress" in ptxt


def test_reconcile_queues_apply_flag_calls_reconcile_apply(tmp_path: Path):
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
        "**Source:** work_id=W-1 kind=x client_id=c1\n\n"
        "---\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    res = runner.invoke(app, [
        "reconcile-queues",
        "--work-queue-path", str(workq),
        "--patch-queue-path", str(patchq),
        "--apply",
    ])
    assert res.exit_code == 0, res.output
    # reconcile-queues first syncs work->patch (should set 🟨), apply should keep consistent
    ptxt = patchq.read_text(encoding="utf-8")
    assert "🟨 in-progress" in ptxt
