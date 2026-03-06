import os
from fastapi.testclient import TestClient

from ae.console_app import app


def test_abuse_api_requires_secret(tmp_path):
    # Use a temporary DB path
    db_path = tmp_path / "t.db"
    os.environ["AE_ENV"] = "dev"
    os.environ["AE_DB_PATH"] = str(db_path)
    os.environ["AE_CONSOLE_SECRET"] = "s"
    client = TestClient(app)

    r = client.get("/api/abuse", params={"db": str(db_path)})
    assert r.status_code in (401, 403)

    r = client.get("/api/abuse", params={"db": str(db_path)}, headers={"x-ae-secret": "s"})
    assert r.status_code == 200
    data = r.json()
    assert "recent" in data and "by_reason" in data


def test_abuse_export_csv(tmp_path):
    db_path = tmp_path / "t.db"
    os.environ["AE_ENV"] = "dev"
    os.environ["AE_DB_PATH"] = str(db_path)
    os.environ["AE_CONSOLE_SECRET"] = "s"
    client = TestClient(app)

    r = client.get("/api/abuse/export", params={"db": str(db_path)}, headers={"x-ae-secret": "s"})
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    assert "ts,ip_hint,endpoint,reason,meta_json" in r.text.splitlines()[0]
