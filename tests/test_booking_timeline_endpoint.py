import os

from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod


def test_booking_timeline_endpoint(tmp_path):
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)

    os.environ["AE_CONSOLE_SECRET"] = "testsecret"
    c = TestClient(app)

    # create lead
    r = c.post(
        "/lead",
        params={"db": db_path},
        json={
            "source": "meta",
            "page_id": "p1",
            "client_id": "c1",
            "name": "Ann",
            "phone": "+66 80 000 0000",
            "email": "ann@example.com",
            "message": "Hi, I'd like to book.",
            "utm": {"utm_source": "meta", "utm_campaign": "cmp1"},
        },
    )
    assert r.status_code == 200
    lead_id = r.json()["lead_id"]

    # outcome -> booked -> emits op.booking.created
    r2 = c.post(
        f"/api/leads/{lead_id}/outcome",
        params={"db": db_path},
        headers={"x-ae-secret": "testsecret"},
        json={"booking_status": "booked", "booking_value": 2500.0, "booking_currency": "THB", "booking_ts": "2026-02-05T00:00:00Z"},
    )
    assert r2.status_code == 200

    # outcome -> confirmed -> emits op.booking.confirmed
    r3 = c.post(
        f"/api/leads/{lead_id}/outcome",
        params={"db": db_path},
        headers={"x-ae-secret": "testsecret"},
        json={"booking_status": "confirmed", "booking_value": 2500.0, "booking_currency": "THB", "booking_ts": "2026-02-05T00:01:00Z"},
    )
    assert r3.status_code == 200

    # booking timeline endpoint
    r4 = c.get(
        f"/api/bookings/{lead_id}/timeline",
        params={"db": db_path},
        headers={"x-ae-secret": "testsecret"},
    )
    assert r4.status_code == 200
    j = r4.json()
    assert j["lead_id"] == lead_id
    assert j["correlation_id"] == f"lead:{lead_id}"
    topics = [it["topic"] for it in j["items"]]
    assert "op.booking.created" in topics
    assert "op.booking.confirmed" in topics

    # labels reflect OP-BOOK-002B richer mapping
    labels = [it["label"] for it in j["items"]]
    assert any("ts=2026-02-05T00:00:00Z" in lab for lab in labels)
    assert any("value=2500.0 THB" in lab for lab in labels)
