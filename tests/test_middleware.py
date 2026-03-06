import os
from fastapi.testclient import TestClient

from ae.public_api import app as public_app


def test_request_id_header_added():
    c = TestClient(public_app)
    r = c.get("/health")
    assert r.status_code == 200
    assert "X-Request-ID" in r.headers
    assert len(r.headers["X-Request-ID"]) > 0


def test_health_hides_db_path_in_prod_by_default(monkeypatch):
    monkeypatch.setenv("AE_ENV", "prod")
    monkeypatch.delenv("AE_HEALTH_SHOW_DB_PATH", raising=False)

    c = TestClient(public_app)
    j = c.get("/health").json()
    db = j.get("db", {})
    assert "ok" in db
    assert "path" not in db  # hidden
