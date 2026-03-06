import importlib

from fastapi.testclient import TestClient


def test_console_abuse_top_endpoint(monkeypatch):
    # Enable abuse + console secret
    monkeypatch.setenv("AE_ABUSE_CONTROLS", "true")
    monkeypatch.setenv("AE_CONSOLE_SECRET", "testsecret")

    # Enable top tracking (local-only path, no Redis in tests)
    monkeypatch.setenv("AE_ABUSE_TOP_ENABLED", "true")
    monkeypatch.setenv("AE_ABUSE_TOP_WINDOW_S", "3600")

    # Deterministic rate limit: allow 1, then 429
    monkeypatch.setenv("AE_RL_COST_LEAD_INTAKE", "1.0")
    monkeypatch.setenv("AE_RATE_LIMIT_BURST", "1.0")
    monkeypatch.setenv("AE_RATE_LIMIT_RPS", "0.0")

    import ae.public_api as public_api
    import ae.console_app as console_app
    importlib.reload(public_api)
    importlib.reload(console_app)

    pub = TestClient(public_api.app)
    con = TestClient(console_app.app)

    payload = {"name": "A", "message": "hi", "utm": {}}

    pub.post("/lead", json=payload)
    pub.post("/lead", json=payload)  # 429
    pub.post("/lead", json=payload)  # 429

    r = con.get("/api/abuse/top?limit=5", headers={"X-AE-SECRET": "testsecret"})
    assert r.status_code == 200
    j = r.json()
    assert j["enabled"] is True
    assert isinstance(j["items"], list)
    assert len(j["items"]) >= 1
    assert "key" in j["items"][0]
    assert "count" in j["items"][0]
