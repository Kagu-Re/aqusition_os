from pathlib import Path
from typer.testing import CliRunner

from ae.cli import app


def test_sla_autopromote_is_idempotent_and_routes_client_id(tmp_path: Path):
    workq = tmp_path / "WORK_QUEUE.md"
    workq.write_text(
        "## Work Queue\n\n"
        "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| W-aaa | P-aaa | c1 | open | rm | 2025-12-01T00:00:00Z |  |  | Old open |  |\n",
        encoding="utf-8",
    )

    sla_policy = tmp_path / "SLA_POLICY.json"
    sla_policy.write_text('{"open_sla_days": 14, "doing_sla_days": 7}\n', encoding="utf-8")

    patchq = tmp_path / "PATCH_QUEUE.md"
    patchq.write_text("", encoding="utf-8")

    runner = CliRunner()
    args = [
        "sla-autopromote",
        "--work-queue-path", str(workq),
        "--sla-policy-path", str(sla_policy),
        "--patch-queue-path", str(patchq),
        "--top-n", "10",
        "--max-doing-per-assignee", "2",
        "--fallback-assignee", "unassigned",
    ]

    r1 = runner.invoke(app, args)
    assert r1.exit_code == 0, r1.output
    r2 = runner.invoke(app, args)
    assert r2.exit_code == 0, r2.output

    ptxt = patchq.read_text(encoding="utf-8")
    # deterministic Q-SLA-* should appear only once
    assert ptxt.count("## Q-SLA-") == 1
    assert "client_id=c1" in ptxt

    wtxt = workq.read_text(encoding="utf-8")
    # new work row should be appended only once
    assert wtxt.count("| W-") >= 2  # includes original + promoted
    assert wtxt.count("auto: sla-autopromote") == 1
