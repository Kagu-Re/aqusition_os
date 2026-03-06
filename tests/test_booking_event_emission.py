import os
from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod
from ae.repo_op_events import list_op_events


def test_booking_event_emission_via_lead_outcome(tmp_path):
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)

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

    # set booking outcome
    r2 = c.post(
        f"/api/leads/{lead_id}/outcome",
        params={"db": db_path},
        headers={"x-ae-secret": "testsecret"},
        json={"booking_status": "booked", "booking_value": 2500.0, "booking_currency": "THB"},
    )
    assert r2.status_code == 200

    # op event exists
    evs = list_op_events(db_path, aggregate_type="booking", aggregate_id=f"lead-{lead_id}", limit=50)
    topics = [e.topic for e in evs]
    assert "op.booking.created" in topics

    # transition: confirm
    r3 = c.post(
        f"/api/leads/{lead_id}/outcome",
        params={"db": db_path},
        headers={"x-ae-secret": "testsecret"},
        json={"booking_status": "confirmed"},
    )
    assert r3.status_code == 200

    evs2 = list_op_events(db_path, aggregate_type="booking", aggregate_id=f"lead-{lead_id}", limit=50)
    topics2 = [e.topic for e in evs2]
    assert "op.booking.confirmed" in topics2


def test_booking_illegal_transition_rejected(tmp_path):
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)

    os.environ["AE_CONSOLE_SECRET"] = "testsecret"
    c = TestClient(app)

    payload = {
        "source": "meta",
        "page_id": "p1",
        "client_id": "c1",
        "name": "Ben",
        "phone": "+66 80 000 0001",
        "email": "ben@example.com",
        "message": "Hello",
        "utm": {"utm_source": "meta"},
    }
    r = c.post("/lead", params={"db": db_path}, json=payload)
    assert r.status_code == 200
    lead_id = r.json()["lead_id"]

    # confirm without created should still update lead_outcome, but op-event should be rejected by transition engine.
    r2 = c.post(
        f"/api/leads/{lead_id}/outcome",
        params={"db": db_path},
        headers={"x-ae-secret": "testsecret"},
        json={"booking_status": "confirmed"},
    )
    assert r2.status_code == 200

    evs = list_op_events(db_path, aggregate_type="booking", aggregate_id=f"lead-{lead_id}", limit=50)
    topics = [e.topic for e in evs]
    assert "op.booking.confirmed" not in topics
