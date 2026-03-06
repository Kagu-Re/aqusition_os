import os
from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod


def seed_basic(db_path: str, c: TestClient):
    lead = c.post("/lead", params={"db": db_path}, json={
        "source":"meta","page_id":"p","client_id":"c","name":"A","phone":"1","email":"a@e.com","message":"m",
        "utm":{"utm_campaign":"cmp1", "utm_source":"meta"}
    }).json()["lead_id"]
    c.post(f"/api/leads/{lead}/outcome", params={"db": db_path}, headers={"x-ae-secret":"testsecret"},
           json={"booking_status":"paid","booking_value":3000,"booking_currency":"THB"})
    c.post("/api/spend/import", params={"db": db_path}, headers={"x-ae-secret":"testsecret"},
           json={"items":[{"day":"2026-02-01","source":"meta","utm_campaign":"cmp1","spend_value":1000,"spend_currency":"THB"}]})


def test_budget_sim_roas_const(tmp_path):
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)
    os.environ["AE_CONSOLE_SECRET"] = "testsecret"
    c = TestClient(app)
    seed_basic(db_path, c)

    j = c.get("/api/sim/budget", params={"db": db_path, "campaign":"cmp1", "delta_spend":1000, "mode":"roas_const"}, headers={"x-ae-secret":"testsecret"}).json()
    assert j["baseline"]["roas"] == 3.0
    assert j["projection"]["delta_revenue"] == 3000.0
    assert j["projected_totals"]["spend"] == 2000.0
    assert j["projected_totals"]["revenue"] == 6000.0
    assert abs(j["projected_totals"]["roas"] - 3.0) < 1e-9
