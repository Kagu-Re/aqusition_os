import os
from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod


def test_spend_import_and_roas(tmp_path):
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)

    os.environ["AE_CONSOLE_SECRET"] = "testsecret"
    c = TestClient(app)

    # create lead with booking_value for revenue
    payload = {
        "source": "meta",
        "page_id": "p1",
        "client_id": "c1",
        "name": "Ann",
        "phone": "+66 80 000 0000",
        "email": "ann@example.com",
        "message": "Hi",
        "utm": {"utm_source": "meta", "utm_campaign": "cmp1"},
    }
    lead_id = c.post("/lead", params={"db": db_path}, json=payload).json()["lead_id"]
    c.post(
        f"/api/leads/{lead_id}/outcome",
        params={"db": db_path},
        headers={"x-ae-secret": "testsecret"},
        json={"booking_status": "booked", "booking_value": 2500.0, "booking_currency": "THB"},
    )

    # import spend
    r = c.post(
        "/api/spend/import",
        params={"db": db_path},
        headers={"x-ae-secret": "testsecret"},
        json={"items": [{"day": "2026-02-01", "source": "meta", "utm_campaign": "cmp1", "spend_value": 1000, "spend_currency": "THB"}]},
    )
    assert r.status_code == 200
    assert r.json()["imported"] == 1

    # roas stats
    r2 = c.get("/api/stats/roas", params={"db": db_path}, headers={"x-ae-secret": "testsecret"})
    j = r2.json()
    assert j["total"]["revenue"] == 2500.0
    assert j["total"]["spend"] == 1000.0
    assert j["total"]["roas"] == 2.5
