from pathlib import Path
from typer.testing import CliRunner

from ae.cli import app


def test_work_sync_patches_updates_status_lines(tmp_path: Path):
    workq = tmp_path / "WORK_QUEUE.md"
    workq.write_text(
        "## Work Queue\n\n"
        "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| W-1 | Q-SLA-1111 | c1 | doing | rm | 2026-01-01T00:00:00Z | 2026-01-01T00:00:00Z |  | A |  |\n"
        "| W-2 | Q-SLA-2222 | c1 | done | rm | 2026-01-01T00:00:00Z | 2026-01-01T00:00:00Z | 2026-01-02T00:00:00Z | B |  |\n",
        encoding="utf-8",
    )

    patchq = tmp_path / "PATCH_QUEUE.md"
    patchq.write_text(
        "## Q-SLA-1111 — SLA: A\n"
        "⬜ planned\n"
        "\n"
        "**Generated:** 2026-01-02T00:00:00Z\n"
        "**Source:** work_id=W-1 kind=open_sla_breach client_id=c1 age_days=20 threshold_days=14\n"
        "\n"
        "---\n\n"
        "## Q-SLA-2222 — SLA: B\n"
        "⬜ planned\n"
        "\n"
        "**Generated:** 2026-01-02T00:00:00Z\n"
        "**Source:** work_id=W-2 kind=doing_sla_breach client_id=c1 age_days=10 threshold_days=7\n"
        "\n"
        "---\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    res = runner.invoke(app, [
        "work-sync-patches",
        "--work-queue-path", str(workq),
        "--patch-queue-path", str(patchq),
    ])
    assert res.exit_code == 0, res.output

    txt = patchq.read_text(encoding="utf-8")
    assert "## Q-SLA-1111" in txt
    assert "🟨 in-progress" in txt
    assert "## Q-SLA-2222" in txt
    assert "✅ done" in txt


def test_work_sync_patches_is_idempotent(tmp_path: Path):
    workq = tmp_path / "WORK_QUEUE.md"
    workq.write_text(
        "## Work Queue\n\n"
        "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| W-1 | Q-SLA-1111 | c1 | doing | rm | 2026-01-01T00:00:00Z | 2026-01-01T00:00:00Z |  | A |  |\n",
        encoding="utf-8",
    )

    patchq = tmp_path / "PATCH_QUEUE.md"
    patchq.write_text(
        "## Q-SLA-1111 — SLA: A\n"
        "🟨 in-progress\n"
        "\n"
        "**Generated:** 2026-01-02T00:00:00Z\n"
        "**Source:** work_id=W-1 kind=open_sla_breach client_id=c1 age_days=20 threshold_days=14\n"
        "\n"
        "---\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    r1 = runner.invoke(app, [
        "work-sync-patches",
        "--work-queue-path", str(workq),
        "--patch-queue-path", str(patchq),
    ])
    assert r1.exit_code == 0, r1.output

    before = patchq.read_text(encoding="utf-8")
    r2 = runner.invoke(app, [
        "work-sync-patches",
        "--work-queue-path", str(workq),
        "--patch-queue-path", str(patchq),
    ])
    assert r2.exit_code == 0, r2.output
    after = patchq.read_text(encoding="utf-8")
    assert before == after
