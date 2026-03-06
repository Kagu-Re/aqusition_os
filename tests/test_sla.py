import json
from typer.testing import CliRunner
from ae.cli import app


def _write_workq(path, rows):
    path.write_text(
        "## Work Queue\n\n"
        "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n",
        encoding="utf-8",
    )


def test_sla_reports_breaches(tmp_path):
    workq = tmp_path / "WORK_QUEUE.md"
    sla_pol = tmp_path / "SLA_POLICY.json"
    # set low thresholds to trigger
    sla_pol.write_text(json.dumps({"open_sla_days": 1, "doing_sla_days": 1, "block_on_breach": False}), encoding="utf-8")

    _write_workq(workq, [
        "| W-AP-aaaaaaaaaa | AP-aaaaaaaaaa | C1 | open | rm | 2026-01-01T00:00:00Z |  |  | Old open |  |",
        "| W-AP-bbbbbbbbbb | AP-bbbbbbbbbb | C2 | doing | rm | 2026-01-01T00:00:00Z | 2026-01-01T00:00:00Z |  | Old doing |  |",
    ])

    runner = CliRunner()
    r = runner.invoke(app, ["sla", "--work-queue-path", str(workq), "--sla-policy-path", str(sla_pol), "--as-json"])
    assert r.exit_code == 0
    data = json.loads(r.stdout)
    assert data["breach_count"] >= 1


def test_preflight_json_includes_sla_section(tmp_path):
    workq = tmp_path / "WORK_QUEUE.md"
    patchq = tmp_path / "PATCH_QUEUE.md"
    env = tmp_path / "ENV.json"
    prof = tmp_path / "PREFLIGHT_PROFILES.json"
    pol = tmp_path / "PREFLIGHT_POLICY.json"
    sla_pol = tmp_path / "SLA_POLICY.json"

    env.write_text(json.dumps({"environment": "prod"}), encoding="utf-8")
    prof.write_text(json.dumps({"prod": {"stale_days": 999, "max_actionable": 999, "max_open_total": 50, "max_doing_total": 10, "max_doing_per_assignee": 3, "max_open_per_client": 10}}), encoding="utf-8")
    pol.write_text(json.dumps({"stale_days": 999, "max_actionable": 999}), encoding="utf-8")
    patchq.write_text("## Patch Queue\n\n", encoding="utf-8")
    sla_pol.write_text(json.dumps({"open_sla_days": 1, "doing_sla_days": 1, "block_on_breach": False}), encoding="utf-8")

    _write_workq(workq, [
        "| W-AP-aaaaaaaaaa | AP-aaaaaaaaaa | C1 | open | rm | 2026-01-01T00:00:00Z |  |  | Old open |  |",
    ])

    runner = CliRunner()
    r = runner.invoke(app, [
        "preflight",
        "--work-queue-path", str(workq),
        "--patch-queue-path", str(patchq),
        "--env-path", str(env),
        "--profiles-path", str(prof),
        "--policy-path", str(pol),
        "--sla-policy-path", str(sla_pol),
        "--as-json",
    ])
    assert r.exit_code == 0
    data = json.loads(r.stdout)
    assert "sla" in data
