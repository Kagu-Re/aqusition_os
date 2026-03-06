import json
from pathlib import Path
from typer.testing import CliRunner

from ae.cli import app


def _seed(workq: Path, patchq: Path):
    workq.write_text(
        "## Work Queue\n\n"
        "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| W-AP-1 | AP-1111111111 |  | blocked | rm | 2026-01-02T00:00:00Z |  |  | c1 - Pixel setup | BLOCKED: waiting on access |\n"
        "| W-AP-2 | AP-2222222222 |  | done | rm | 2026-01-03T00:00:00Z | 2026-01-03T01:00:00Z | 2026-01-04T00:00:00Z | c1 - Launch | shipped |\n"
        "| W-AP-3 | AP-3333333333 |  | open | bot | 2026-01-03T00:00:00Z |  |  | c2 - Other |  |\n",
        encoding="utf-8",
    )

    patchq.write_text(
        "## Patch Queue\n\n"
        "## AP-aaaaaaaaaa\n"
        "- client_id: c1\n"
        "- platform: meta\n"
        "- since_iso: 2026-01-01T00:00:00Z\n\n"
        "## AP-bbbbbbbbbb\n"
        "- client_id: c2\n"
        "- platform: meta\n"
        "- since_iso: 2026-01-01T00:00:00Z\n",
        encoding="utf-8",
    )


def test_client_status_json(tmp_path):
    workq = tmp_path / "WORK_QUEUE.md"
    patchq = tmp_path / "PATCH_QUEUE.md"
    _seed(workq, patchq)

    runner = CliRunner()
    r = runner.invoke(app, ["client-status", "--client-id", "c1", "--work-queue-path", str(workq), "--patch-queue-path", str(patchq), "--as-json", "--last", "3650", "--stale-days", "0"])
    assert r.exit_code == 0, r.stdout
    obj = json.loads(r.stdout)

    assert obj["client_id"] == "c1"
    assert obj["work_total"] == 2
    assert obj["status_counts"]["blocked"] == 1
    assert obj["status_counts"]["done"] == 1
    assert obj["latest_autoplan_patch_id"] == "AP-aaaaaaaaaa"
    assert obj["top_blocked_reasons"][0]["reason"] == "waiting on access"
