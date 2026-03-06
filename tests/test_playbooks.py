import os
from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod


def test_playbooks_endpoint(tmp_path):
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)
    os.environ["AE_CONSOLE_SECRET"] = "testsecret"
    c = TestClient(app)

    j = c.get("/api/playbooks", headers={"x-ae-secret":"testsecret"}).json()
    assert "playbooks" in j
    assert isinstance(j["playbooks"], dict)
