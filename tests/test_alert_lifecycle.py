import os
from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod


def test_alert_ack_and_resolve(tmp_path):
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)
    os.environ["AE_CONSOLE_SECRET"] = "testsecret"
    c = TestClient(app)

    # create an alert (spend without revenue)
    c.post("/api/spend/import", params={"db": db_path}, headers={"x-ae-secret":"testsecret"},
           json={"items":[{"day":"2026-02-01","source":"meta","utm_campaign":"cmpL","spend_value":1500,"spend_currency":"THB"}]})
    c.put("/api/alerts/thresholds", params={"db": db_path}, headers={"x-ae-secret":"testsecret"},
          json={"max_spend_no_revenue": 1000, "min_roas": 0.0, "max_cpl": 999999, "min_booking_rate": 0.0})
    c.post("/api/alerts/evaluate", params={"db": db_path}, headers={"x-ae-secret":"testsecret"})

    # list and pick latest id
    lst = c.get("/api/alerts/list", params={"db": db_path, "status":"open"}, headers={"x-ae-secret":"testsecret"}).json()
    assert lst["alerts"]
    aid = lst["alerts"][0]["id"]

    # ack
    a = c.post("/api/alerts/ack", params={"db": db_path}, headers={"x-ae-secret":"testsecret"}, json={"id": aid, "note":"seen"}).json()
    assert a["status"] == "ack"

    # resolve
    r = c.post("/api/alerts/resolve", params={"db": db_path}, headers={"x-ae-secret":"testsecret"}, json={"id": aid, "note":"fixed"}).json()
    assert r["status"] == "resolved"
