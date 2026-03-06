import os
from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod


def test_lead_outcome_and_revenue(tmp_path):
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)

    # set secret so operator endpoints work
    os.environ["AE_CONSOLE_SECRET"] = "testsecret"
    c = TestClient(app)

    # create lead (public endpoint)
    payload = {
        "source": "meta",
        "page_id": "p1",
        "client_id": "c1",
        "name": "Ann",
        "phone": "+66 80 000 0000",
        "email": "ann@example.com",
        "message": "Hi, I'd like to book.",
        "utm": {"utm_source": "meta", "utm_campaign": "cmp1"},
    }
    r = c.post("/lead", params={"db": db_path}, json=payload)
    assert r.status_code == 200
    lead_id = r.json()["lead_id"]

    # update outcome (operator)
    r2 = c.post(
        f"/api/leads/{lead_id}/outcome",
        params={"db": db_path},
        headers={"x-ae-secret": "testsecret"},
        json={"booking_status": "booked", "booking_value": 2500.0, "booking_currency": "THB"},
    )
    assert r2.status_code == 200

    # revenue stats
    r3 = c.get("/api/stats/revenue", params={"db": db_path}, headers={"x-ae-secret": "testsecret"})
    assert r3.status_code == 200
    j3 = r3.json()
    assert j3["total"]["count"] == 1
    assert j3["total"]["value"] == 2500.0
    assert any(it["source"] == "meta" for it in j3["by_source"])
