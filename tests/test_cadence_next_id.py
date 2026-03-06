import tempfile
from pathlib import Path
from ae import cadence

def test_next_patch_id_increments():
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        pid1 = cadence.next_patch_id(repo, date_yyyymmdd="20260130")
        assert pid1 == "P-20260130-0001"
        cadence.create_patch(repo, pid1, "v0.0.1", "patch", "x")
        pid2 = cadence.next_patch_id(repo, date_yyyymmdd="20260130")
        assert pid2 == "P-20260130-0002"
