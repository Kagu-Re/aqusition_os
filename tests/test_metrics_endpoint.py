from fastapi.testclient import TestClient

from ae.public_api import app


def test_metrics_endpoint_smoke(monkeypatch):
    monkeypatch.delenv("AE_METRICS_TOKEN", raising=False)
    monkeypatch.delenv("AE_METRICS_ALLOW_CIDRS", raising=False)

    client = TestClient(app)
    r = client.get("/metrics")
    assert r.status_code == 200
    data = r.json()
    assert "http" in data
    assert "abuse_controls" in data
