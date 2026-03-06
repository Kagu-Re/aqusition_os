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


def test_capacity_command_outputs_counts(tmp_path):
    workq = tmp_path / "WORK_QUEUE.md"
    env = tmp_path / "ENV.json"
    prof = tmp_path / "PREFLIGHT_PROFILES.json"
    pol = tmp_path / "PREFLIGHT_POLICY.json"

    env.write_text(json.dumps({"environment": "prod"}), encoding="utf-8")
    prof.write_text(json.dumps({"prod": {"stale_days": 7, "max_actionable": 0, "max_open_total": 50, "max_doing_total": 10, "max_doing_per_assignee": 3, "max_open_per_client": 10}}), encoding="utf-8")
    pol.write_text(json.dumps({"stale_days": 7, "max_actionable": 0}), encoding="utf-8")

    _write_workq(workq, [
        "| W-AP-aaaaaaaaaa | AP-aaaaaaaaaa | C1 | open | rm | 2026-01-01T00:00:00Z |  |  | T1 |  |",
        "| W-AP-bbbbbbbbbb | AP-bbbbbbbbbb | C1 | doing | rm | 2026-01-01T00:00:00Z | 2026-01-01T00:00:00Z |  | T2 |  |",
    ])

    runner = CliRunner()
    r = runner.invoke(app, ["capacity", "--work-queue-path", str(workq), "--env-path", str(env), "--profiles-path", str(prof), "--policy-path", str(pol)])
    assert r.exit_code == 0
    assert "capacity: env=prod" in r.stdout


def test_preflight_fails_when_open_cap_exceeded(tmp_path):
    workq = tmp_path / "WORK_QUEUE.md"
    patchq = tmp_path / "PATCH_QUEUE.md"
    env = tmp_path / "ENV.json"
    prof = tmp_path / "PREFLIGHT_PROFILES.json"
    pol = tmp_path / "PREFLIGHT_POLICY.json"

    env.write_text(json.dumps({"environment": "prod"}), encoding="utf-8")
    prof.write_text(json.dumps({"prod": {"stale_days": 7, "max_actionable": 0, "max_open_total": 1, "max_doing_total": 10, "max_doing_per_assignee": 3, "max_open_per_client": 10}}), encoding="utf-8")
    pol.write_text(json.dumps({"stale_days": 7, "max_actionable": 0}), encoding="utf-8")

    patchq.write_text("## Patch Queue\n\n", encoding="utf-8")

    _write_workq(workq, [
        "| W-AP-aaaaaaaaaa | AP-aaaaaaaaaa | C1 | open | rm | 2026-01-01T00:00:00Z |  |  | T1 |  |",
        "| W-AP-bbbbbbbbbb | AP-bbbbbbbbbb | C2 | open | rm | 2026-01-01T00:00:00Z |  |  | T2 |  |",
    ])

    runner = CliRunner()
    r = runner.invoke(app, [
        "preflight",
        "--work-queue-path", str(workq),
        "--patch-queue-path", str(patchq),
        "--env-path", str(env),
        "--profiles-path", str(prof),
        "--policy-path", str(pol),
    ])
    assert r.exit_code == 2
