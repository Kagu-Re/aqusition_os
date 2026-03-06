import os
from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod


def test_alerts_evaluate_creates_campaign_alert(tmp_path):
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)
    os.environ["AE_CONSOLE_SECRET"] = "testsecret"
    c = TestClient(app)

    # spend but no leads/revenue for cmpX
    c.post("/api/spend/import", params={"db": db_path}, headers={"x-ae-secret":"testsecret"},
           json={"items":[{"day":"2026-02-01","source":"meta","utm_campaign":"cmpX","spend_value":1500,"spend_currency":"THB"}]})

    # tighten threshold so it definitely triggers
    c.put("/api/alerts/thresholds", params={"db": db_path}, headers={"x-ae-secret":"testsecret"},
          json={"max_spend_no_revenue": 1000, "min_roas": 0.0, "max_cpl": 999999, "min_booking_rate": 0.0})

    j = c.post("/api/alerts/evaluate", params={"db": db_path}, headers={"x-ae-secret":"testsecret"}).json()
    assert j["created"] >= 1

    lst = c.get("/api/alerts/list", params={"db": db_path}, headers={"x-ae-secret":"testsecret"}).json()
    assert len(lst["alerts"]) >= 1
    a = lst["alerts"][0]
    assert a["type"] in ("campaign_spend_no_revenue", "kpi_below_threshold", "kpi_above_threshold")
