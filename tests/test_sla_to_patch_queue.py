import json
from pathlib import Path
from typer.testing import CliRunner
from ae.cli import app


def _write_workq(path, rows):
    path.write_text(
        "## Work Queue\n\n"
        "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n",
        encoding="utf-8",
    )


def test_sla_to_patch_queue_appends_deterministic_sections(tmp_path):
    workq = tmp_path / "WORK_QUEUE.md"
    sla_pol = tmp_path / "SLA_POLICY.json"
    patchq = tmp_path / "PATCH_QUEUE.md"

    sla_pol.write_text(json.dumps({"open_sla_days": 1, "doing_sla_days": 1, "block_on_breach": False}), encoding="utf-8")
    patchq.write_text("# Patch Queue (append-only)\n\n---\n\n", encoding="utf-8")

    _write_workq(workq, [
        "| W-AP-aaaaaaaaaa | AP-aaaaaaaaaa | C1 | open | rm | 2026-01-01T00:00:00Z |  |  | Old open |  |",
    ])

    runner = CliRunner()
    r = runner.invoke(app, ["sla-to-patch-queue", "--work-queue-path", str(workq), "--sla-policy-path", str(sla_pol), "--patch-queue-path", str(patchq), "--top-n", "5"])
    assert r.exit_code == 0

    txt = patchq.read_text(encoding="utf-8")
    assert "Q-SLA-" in txt
    # second run should be idempotent
    r2 = runner.invoke(app, ["sla-to-patch-queue", "--work-queue-path", str(workq), "--sla-policy-path", str(sla_pol), "--patch-queue-path", str(patchq), "--top-n", "5"])
    assert r2.exit_code == 0
    txt2 = patchq.read_text(encoding="utf-8")
    assert txt2.count("Q-SLA-") == txt.count("Q-SLA-")
