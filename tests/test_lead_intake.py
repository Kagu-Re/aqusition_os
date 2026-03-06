import os
from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod


def test_lead_intake_and_list(tmp_path):
    os.environ.pop("AE_CONSOLE_SECRET", None)
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)

    c = TestClient(app)

    payload = {
        "source": "webform",
        "page_id": "p1",
        "client_id": "c1",
        "name": "Ann",
        "phone": "+66 80 000 0000",
        "email": "ann@example.com",
        "message": "Hi, I'd like to book.",
        "utm": {"utm_source": "meta", "utm_campaign": "test"},
    }
    r = c.post("/lead", params={"db": db_path}, json=payload)
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is True
    assert j["lead_id"] >= 1

    r2 = c.get("/api/leads", params={"db": db_path, "limit": 10})
    assert r2.status_code == 200
    j2 = r2.json()
    assert j2["count"] >= 1
    assert j2["items"][0]["client_id"] == "c1"
