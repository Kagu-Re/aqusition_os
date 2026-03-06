import os
from fastapi.testclient import TestClient

from ae.console_app import app


def test_console_abuse_requires_secret(tmp_path):
    db_path = tmp_path / "t.db"
    os.environ["AE_ENV"] = "dev"
    os.environ["AE_DB_PATH"] = str(db_path)
    os.environ["AE_CONSOLE_SECRET"] = "s"
    client = TestClient(app)

    r = client.get("/console/abuse", params={"db": str(db_path)})
    assert r.status_code in (401, 403)

    r = client.get("/console/abuse", params={"db": str(db_path)}, headers={"x-ae-secret": "s"})
    assert r.status_code == 200
    assert "Abuse Monitor" in r.text
    assert "/api/abuse/export" in r.text
