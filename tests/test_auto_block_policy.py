import importlib

from fastapi.testclient import TestClient


def test_auto_block_policy_triggers_rate_limit_and_exposes_metric(monkeypatch):
    # Configure env BEFORE importing the app module (public_api builds app at import time)
    monkeypatch.setenv("AE_ABUSE_CONTROLS", "true")
    monkeypatch.setenv("AE_RL_COST_LEAD_INTAKE", "1.0")
    monkeypatch.setenv("AE_RATE_LIMIT_BURST", "1.0")
    monkeypatch.setenv("AE_RATE_LIMIT_RPS", "0.0")

    monkeypatch.setenv("AE_AUTO_BLOCK_ENABLED", "true")
    monkeypatch.setenv("AE_AUTO_BLOCK_RATE_LIMIT_HITS", "2")
    monkeypatch.setenv("AE_AUTO_BLOCK_WINDOW_S", "60")
    monkeypatch.setenv("AE_AUTO_BLOCK_TTL_S", "60")

    import ae.public_api as public_api
    importlib.reload(public_api)

    client = TestClient(public_api.app)

    payload = {"name": "A", "message": "hi", "utm": {}}

    r1 = client.post("/lead", json=payload)
    assert r1.status_code in (200, 201, 400)

    r2 = client.post("/lead", json=payload)
    assert r2.status_code == 429

    r3 = client.post("/lead", json=payload)
    assert r3.status_code == 429

    # /metrics is exempt from rate limit to avoid self-inflicted blindness
    m = client.get("/metrics")
    assert m.status_code == 200
    j = m.json()
    assert "abuse_controls" in j
    assert "auto_block_total" in j["abuse_controls"]
