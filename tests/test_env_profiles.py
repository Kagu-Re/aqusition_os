import json
from pathlib import Path
from typer.testing import CliRunner
from ae.cli import app


def test_env_command_reports_env_and_policy(tmp_path):
    env = tmp_path / "ENV.json"
    profiles = tmp_path / "PREFLIGHT_PROFILES.json"
    policy = tmp_path / "PREFLIGHT_POLICY.json"

    env.write_text(json.dumps({"environment": "prod"}), encoding="utf-8")
    profiles.write_text(json.dumps({"prod": {"stale_days": 3, "max_actionable": 0}}), encoding="utf-8")
    policy.write_text(json.dumps({"stale_days": 7, "max_actionable": 0}), encoding="utf-8")

    runner = CliRunner()
    r = runner.invoke(app, ["env", "--env-path", str(env), "--profiles-path", str(profiles), "--policy-path", str(policy)])
    assert r.exit_code == 0
    assert "Environment: prod" in r.stdout
    assert "stale_days: 3" in r.stdout


def test_preflight_uses_profile_policy(tmp_path):
    workq = tmp_path / "WORK_QUEUE.md"
    patchq = tmp_path / "PATCH_QUEUE.md"
    env = tmp_path / "ENV.json"
    profiles = tmp_path / "PREFLIGHT_PROFILES.json"
    policy = tmp_path / "PREFLIGHT_POLICY.json"

    # stale_days=0 in profile makes the item stale immediately; max_actionable=0 makes it fail
    env.write_text(json.dumps({"environment": "prod"}), encoding="utf-8")
    profiles.write_text(json.dumps({"prod": {"stale_days": 0, "max_actionable": 0}}), encoding="utf-8")
    policy.write_text(json.dumps({"stale_days": 7, "max_actionable": 0}), encoding="utf-8")

    workq.write_text(
        "## Work Queue\n\n"
        "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| W-AP-aaaaaaaaaa | AP-aaaaaaaaaa |  | open | rm | 2026-01-01T00:00:00Z |  |  | T1 |  |\n",
        encoding="utf-8",
    )
    patchq.write_text("## Patch Queue\n\n", encoding="utf-8")

    runner = CliRunner()
    r = runner.invoke(app, [
        "preflight",
        "--work-queue-path", str(workq),
        "--patch-queue-path", str(patchq),
        "--env-path", str(env),
        "--profiles-path", str(profiles),
        "--policy-path", str(policy),
    ])
    assert r.exit_code == 2
