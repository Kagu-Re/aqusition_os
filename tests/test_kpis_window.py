import os
from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod


def test_kpis_window(tmp_path):
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)
    os.environ["AE_CONSOLE_SECRET"] = "testsecret"
    c = TestClient(app)

    # lead day inferred from ts; but we can just create leads and spend on the same window
    lead = c.post("/lead", params={"db": db_path}, json={
        "source":"meta","page_id":"p","client_id":"c","name":"A","phone":"1","email":"a@e.com","message":"m",
        "utm":{"utm_campaign":"cmp1", "utm_source":"meta"}
    }).json()["lead_id"]
    c.post(f"/api/leads/{lead}/outcome", params={"db": db_path}, headers={"x-ae-secret":"testsecret"},
           json={"booking_status":"booked","booking_value":2000,"booking_currency":"THB"})

    c.post("/api/spend/import", params={"db": db_path}, headers={"x-ae-secret":"testsecret"},
           json={"items":[{"day":"2026-02-01","source":"meta","utm_campaign":"cmp1","spend_value":1000,"spend_currency":"THB"}]})

    # no window (all time)
    j = c.get("/api/stats/kpis", params={"db": db_path}, headers={"x-ae-secret":"testsecret"}).json()
    assert j["totals"]["revenue"] == 2000.0
    assert j["totals"]["spend"] == 1000.0
    assert j["totals"]["roas"] == 2.0

    # spend-only window should affect spend but leads window depends on lead ts day (today in UTC)
    j2 = c.get("/api/stats/kpis", params={"db": db_path, "day_from":"2026-02-01", "day_to":"2026-02-01"}, headers={"x-ae-secret":"testsecret"}).json()
    assert j2["totals"]["spend"] == 1000.0
