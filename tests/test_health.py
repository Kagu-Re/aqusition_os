from fastapi.testclient import TestClient

from ae.public_api import app as public_app
from ae.console_app import app as console_app


def test_public_health_and_ready():
    c = TestClient(public_app)
    r = c.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is True
    assert "version" in j
    r2 = c.get("/ready")
    assert r2.status_code == 200
    j2 = r2.json()
    assert "ok" in j2


def test_console_health_and_ready():
    c = TestClient(console_app)
    r = c.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is True
    r2 = c.get("/ready")
    assert r2.status_code == 200
