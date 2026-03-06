from pathlib import Path
from typer.testing import CliRunner

from ae.cli import app
from ae.ops_writer import make_patch_item, append_patch_queue


def test_patchqueue_to_work_promotes_and_dedups(tmp_path):
    patchq = tmp_path / "PATCH_QUEUE.md"
    workq = tmp_path / "WORK_QUEUE.md"

    # Seed a patch entry
    item = make_patch_item(
        client_id="c1",
        platform="meta",
        overall_status="RED",
        since_iso="2026-01-01T00:00:00Z",
        content_md="# AutoPlan for c1\n\n- patch_id: `AP-aaaaaaaaaa`\n- client_id: `c1`\n\n- [ ] step\n",
    )
    # Force patch_id to fixed value for this test (override deterministic output)
    item2 = item.__class__(patch_id="AP-aaaaaaaaaa", timestamp_utc=item.timestamp_utc, title=item.title, body_md=item.body_md.replace(item.patch_id, "AP-aaaaaaaaaa"))
    append_patch_queue(str(patchq), item2)

    runner = CliRunner()
    res1 = runner.invoke(app, ["patchqueue-to-work", "--patch-id", "AP-aaaaaaaaaa", "--assignee", "rm", "--patch-queue-path", str(patchq), "--work-queue-path", str(workq)])
    assert res1.exit_code == 0, res1.stdout
    txt1 = workq.read_text(encoding="utf-8")
    assert "W-AP-aaaaaaaaaa" in txt1
    assert txt1.count("W-AP-aaaaaaaaaa") == 1

    # Run again: should dedup
    res2 = runner.invoke(app, ["patchqueue-to-work", "--patch-id", "AP-aaaaaaaaaa", "--assignee", "rm", "--patch-queue-path", str(patchq), "--work-queue-path", str(workq)])
    assert res2.exit_code == 0, res2.stdout
    txt2 = workq.read_text(encoding="utf-8")
    assert txt2.count("W-AP-aaaaaaaaaa") == 1
