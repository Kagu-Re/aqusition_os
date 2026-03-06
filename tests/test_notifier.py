import os
from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod
from ae import repo


def test_notifier_config_roundtrip(tmp_path):
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)
    os.environ["AE_CONSOLE_SECRET"] = "testsecret"
    c = TestClient(app)

    # set config (file only)
    j = c.put("/api/notify/config", params={"db": db_path}, headers={"x-ae-secret":"testsecret"},
              json={"file_path": str(tmp_path / "notify.log"), "throttle_seconds": 0}).json()
    assert "file_path" in j

    # test notify writes file and returns report
    rep = c.post("/api/notify/test", params={"db": db_path}, headers={"x-ae-secret":"testsecret"}).json()
    assert "channels" in rep
    assert rep["channels"]["file"]["ok"] in (True, False)


def test_evaluate_alerts_notify_flag(tmp_path):
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)
    os.environ["AE_CONSOLE_SECRET"] = "testsecret"
    c = TestClient(app)

    # configure file notifier and no throttle
    c.put("/api/notify/config", params={"db": db_path}, headers={"x-ae-secret":"testsecret"},
          json={"file_path": str(tmp_path / "notify.log"), "throttle_seconds": 0})

    # create spend so alert triggers
    c.post("/api/spend/import", params={"db": db_path}, headers={"x-ae-secret":"testsecret"},
           json={"items":[{"day":"2026-02-01","source":"meta","utm_campaign":"cmpN","spend_value":1500,"spend_currency":"THB"}]})

    c.put("/api/alerts/thresholds", params={"db": db_path}, headers={"x-ae-secret":"testsecret"},
          json={"max_spend_no_revenue": 1000, "min_roas": 0.0, "max_cpl": 999999, "min_booking_rate": 0.0})

    out = c.post("/api/alerts/evaluate", params={"db": db_path, "notify": 1}, headers={"x-ae-secret":"testsecret"}).json()
    assert "notify" in out
    assert out["notify"]["sent"] >= 1
