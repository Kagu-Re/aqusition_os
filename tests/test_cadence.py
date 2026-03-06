import tempfile
from pathlib import Path
from ae import cadence

def test_create_patch_and_verify_release_fails_when_tests_fail():
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        meta = cadence.create_patch(repo, "P-20260130-9999", "v0.1.2", "patch", "test")
        assert meta.patch_id == "P-20260130-9999"

        log = repo / "LOG_HORIZON.md"
        res = cadence.verify_release(repo, meta.patch_id, log, artifacts=[], notes=None, next_=None)
        assert res["ok"] is False
        assert res["reason"] == "tests_failed"
