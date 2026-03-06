import os
from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod


def test_clients_api_list_and_upsert(tmp_path):
    db_path = str(tmp_path / "ae.db")
    dbmod.init_db(db_path)

    os.environ["AE_CONSOLE_SECRET"] = "s"

    c = TestClient(app)

    # Upsert
    payload = {
        "slug": "barber-cm",
        "name": "Plumber CM",
        "industry": "plumber",
        "geo_country": "TH",
        "geo": "chiang mai",
        "service_area": ["chiang mai"],
        "primary_phone": "+66-400-000-001",
        "lead_email": "owner@example.com",
        "status": "draft",
        "offer": "pipe fix",
    }
    r = c.post("/api/clients", params={"db_path": db_path}, headers={"X-AE-SECRET": "s"}, json=payload)
    assert r.status_code == 200, r.text
    out = r.json()["client"]
    assert out["client_id"] == "barber-cm"
    assert out["client_name"] == "Plumber CM"

    # List
    r = c.get("/api/clients", params={"db_path": db_path, "limit": 50}, headers={"X-AE-SECRET": "s"})
    assert r.status_code == 200, r.text
    items = r.json()["clients"]
    assert any(x["client_id"] == "barber-cm" for x in items)

    # Status change
    r = c.post(f"/api/clients/barber-cm/status", params={"db_path": db_path}, headers={"X-AE-SECRET": "s"}, json={"status": "live"})
    assert r.status_code == 200, r.text
    assert r.json()["client"]["status"] == "live"
