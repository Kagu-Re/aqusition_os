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


def test_sla_plan_writes_markdown(tmp_path):
    workq = tmp_path / "WORK_QUEUE.md"
    sla_pol = tmp_path / "SLA_POLICY.json"
    out_md = tmp_path / "SLA_PATCH_LIST.md"

    sla_pol.write_text(json.dumps({"open_sla_days": 1, "doing_sla_days": 1, "block_on_breach": False}), encoding="utf-8")
    _write_workq(workq, [
        "| W-AP-aaaaaaaaaa | AP-aaaaaaaaaa | C1 | open | rm | 2026-01-01T00:00:00Z |  |  | Old open |  |",
    ])

    runner = CliRunner()
    r = runner.invoke(app, ["sla-plan", "--work-queue-path", str(workq), "--sla-policy-path", str(sla_pol), "--out-path", str(out_md)])
    assert r.exit_code == 0
    assert out_md.exists()
    txt = out_md.read_text(encoding="utf-8")
    assert "SLA Patch List" in txt
    assert "| priority |" in txt
