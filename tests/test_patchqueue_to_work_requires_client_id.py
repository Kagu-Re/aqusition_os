from pathlib import Path
from typer.testing import CliRunner
from ae.cli import app


def test_patchqueue_to_work_requires_client_id(tmp_path):
    patchq = tmp_path / "PATCH_QUEUE.md"
    workq = tmp_path / "WORK_QUEUE.md"

    patchq.write_text(
        "## Patch Queue\n\n"
        "## AP-aaaaaaaaaa\n"
        "- platform: meta\n"
        "- since_iso: 2026-01-01T00:00:00Z\n"
        "- objective: test\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    r = runner.invoke(app, ["patchqueue-to-work", "--patch-id", "AP-aaaaaaaaaa", "--patch-queue-path", str(patchq), "--work-queue-path", str(workq)])
    assert r.exit_code != 0
    assert "client_id is required" in (r.stdout + r.stderr)
