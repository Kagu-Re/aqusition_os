from fastapi.testclient import TestClient

from ae.console_app import app


def test_blocklist_routes_require_secret(monkeypatch):
    monkeypatch.setenv("AE_CONSOLE_SECRET", "testsecret")
    client = TestClient(app)
    r = client.get("/api/blocklist/ttl", params={"key": "1.2.3.4"})
    assert r.status_code == 401


def test_blocklist_routes_redis_not_configured(monkeypatch):
    monkeypatch.setenv("AE_CONSOLE_SECRET", "testsecret")
    monkeypatch.delenv("AE_REDIS_URL", raising=False)

    client = TestClient(app)
    r = client.post(
        "/api/blocklist/add",
        headers={"X-AE-SECRET": "testsecret"},
        params={"key": "1.2.3.4", "ttl_s": 60},
    )
    assert r.status_code == 200
    assert r.json().get("error") == "redis_not_configured"
