import os
from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod


def test_campaign_stats_endpoint(tmp_path):
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)
    os.environ["AE_CONSOLE_SECRET"] = "testsecret"
    c = TestClient(app)

    # create 2 leads in cmp1, 1 booking
    lead1 = c.post("/lead", params={"db": db_path}, json={
        "source":"meta","page_id":"p","client_id":"c","name":"A","phone":"1","email":"a@e.com","message":"m",
        "utm":{"utm_campaign":"cmp1", "utm_source":"meta"}
    }).json()["lead_id"]
    lead2 = c.post("/lead", params={"db": db_path}, json={
        "source":"meta","page_id":"p","client_id":"c","name":"B","phone":"2","email":"b@e.com","message":"m",
        "utm":{"utm_campaign":"cmp1", "utm_source":"meta"}
    }).json()["lead_id"]
    c.post(f"/api/leads/{lead1}/outcome", params={"db": db_path}, headers={"x-ae-secret":"testsecret"},
           json={"booking_status":"paid","booking_value":3000,"booking_currency":"THB"})

    # spend for cmp1 and cmp2 (no leads)
    c.post("/api/spend/import", params={"db": db_path}, headers={"x-ae-secret":"testsecret"},
           json={"items":[
               {"day":"2026-02-01","source":"meta","utm_campaign":"cmp1","spend_value":1000,"spend_currency":"THB"},
               {"day":"2026-02-01","source":"google","utm_campaign":"cmp2","spend_value":500,"spend_currency":"THB"},
           ]})

    j = c.get("/api/stats/campaigns", params={"db": db_path, "sort_by":"roas"}, headers={"x-ae-secret":"testsecret"}).json()
    assert "campaigns" in j
    # cmp1 should have roas 3.0 and status scale
    cmp1 = [x for x in j["campaigns"] if x["campaign"] == "cmp1"][0]
    assert cmp1["revenue"] == 3000.0
    assert cmp1["spend"] == 1000.0
    assert abs(cmp1["roas"] - 3.0) < 1e-9
    assert cmp1["status"] == "scale"
    # cmp2 should be test_failed (spend>0 revenue=0)
    cmp2 = [x for x in j["campaigns"] if x["campaign"] == "cmp2"][0]
    assert cmp2["status"] == "test_failed"
