import os
from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod


def test_spend_upsert_update_delete(tmp_path):
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)

    os.environ["AE_CONSOLE_SECRET"] = "testsecret"
    c = TestClient(app)

    # upsert import twice -> should still have 1 row
    items = [{"day": "2026-02-01", "source": "meta", "utm_campaign": "cmp1", "spend_value": 1000, "spend_currency": "THB"}]
    r1 = c.post("/api/spend/import", params={"db": db_path}, headers={"x-ae-secret": "testsecret"}, json={"items": items})
    assert r1.status_code == 200
    r2 = c.post("/api/spend/import", params={"db": db_path}, headers={"x-ae-secret": "testsecret"}, json={"items": [{"day":"2026-02-01","source":"meta","utm_campaign":"cmp1","spend_value":1500,"spend_currency":"THB"}]})
    assert r2.status_code == 200

    lst = c.get("/api/spend", params={"db": db_path, "limit": 50}, headers={"x-ae-secret": "testsecret"}).json()
    assert lst["count"] == 1
    spend_id = lst["items"][0]["spend_id"]
    assert lst["items"][0]["spend_value"] == 1500.0

    # update
    ru = c.post(f"/api/spend/{spend_id}", params={"db": db_path}, headers={"x-ae-secret": "testsecret"}, json={"spend_value": 2000})
    assert ru.status_code == 200
    lst2 = c.get("/api/spend", params={"db": db_path, "limit": 50}, headers={"x-ae-secret": "testsecret"}).json()
    assert lst2["items"][0]["spend_value"] == 2000.0

    # delete
    rd = c.delete(f"/api/spend/{spend_id}", params={"db": db_path}, headers={"x-ae-secret": "testsecret"})
    assert rd.status_code == 200
    lst3 = c.get("/api/spend", params={"db": db_path, "limit": 50}, headers={"x-ae-secret": "testsecret"}).json()
    assert lst3["count"] == 0
