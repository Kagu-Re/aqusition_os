import os

from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod
from ae.repo_op_events import list_op_events
from ae.repo_states import get_state


def _client() -> TestClient:
    os.environ["AE_CONSOLE_SECRET"] = "testsecret"
    return TestClient(app)


def _create_lead(db_path: str) -> int:
    c = _client()
    payload = {
        "source": "meta",
        "page_id": "p1",
        "client_id": "c1",
        "name": "Ann",
        "phone": "+66 80 000 0000",
        "email": "ann@example.com",
        "message": "Hi",
        "utm": {"utm_source": "meta"},
    }
    r = c.post("/lead", params={"db": db_path}, json=payload)
    assert r.status_code == 200
    return r.json()["lead_id"]


def _set_booking_status(db_path: str, lead_id: int, status: str) -> None:
    c = _client()
    r = c.post(
        f"/api/leads/{lead_id}/outcome",
        params={"db": db_path},
        headers={"x-ae-secret": "testsecret"},
        json={"booking_status": status, "booking_value": 2500.0, "booking_currency": "THB"},
    )
    assert r.status_code == 200


def test_payment_events_created_and_captured_direct(tmp_path):
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)

    lead_id = _create_lead(db_path)
    _set_booking_status(db_path, lead_id, "booked")

    c = _client()
    payment_id = "pay1"
    r = c.post(
        "/api/payments",
        params={"db": db_path},
        headers={"x-ae-secret": "testsecret"},
        json={
            "payment_id": payment_id,
            "booking_id": f"lead-{lead_id}",
            "lead_id": lead_id,
            "amount": 1000.0,
            "currency": "THB",
            "provider": "manual",
            "method": "cash",
            "status": "pending",
        },
    )
    assert r.status_code == 200

    evs = list_op_events(db_path, aggregate_type="payment", aggregate_id=payment_id, limit=50)
    topics = [e.topic for e in evs]
    assert "op.payment.created" in topics
    assert get_state(db_path, aggregate_type="payment", aggregate_id=payment_id) == "pending"

    # confirm booking to allow capture
    _set_booking_status(db_path, lead_id, "confirmed")

    r2 = c.patch(
        f"/api/payments/{payment_id}/status",
        params={"db": db_path},
        headers={"x-ae-secret": "testsecret"},
        json={"status": "captured"},
    )
    assert r2.status_code == 200

    evs2 = list_op_events(db_path, aggregate_type="payment", aggregate_id=payment_id, limit=50)
    topics2 = [e.topic for e in evs2]
    assert "op.payment.status_changed" in topics2
    assert "op.payment.captured_direct" in topics2
    assert get_state(db_path, aggregate_type="payment", aggregate_id=payment_id) == "captured"


def test_payment_events_authorized_then_captured(tmp_path):
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)

    lead_id = _create_lead(db_path)
    _set_booking_status(db_path, lead_id, "confirmed")

    c = _client()
    payment_id = "pay2"
    r = c.post(
        "/api/payments",
        params={"db": db_path},
        headers={"x-ae-secret": "testsecret"},
        json={
            "payment_id": payment_id,
            "booking_id": f"lead-{lead_id}",
            "lead_id": lead_id,
            "amount": 1000.0,
            "currency": "THB",
            "provider": "manual",
            "method": "bank_transfer",
            "status": "pending",
        },
    )
    assert r.status_code == 200

    r1 = c.patch(
        f"/api/payments/{payment_id}/status",
        params={"db": db_path},
        headers={"x-ae-secret": "testsecret"},
        json={"status": "authorized"},
    )
    assert r1.status_code == 200
    assert get_state(db_path, aggregate_type="payment", aggregate_id=payment_id) == "authorized"

    r2 = c.patch(
        f"/api/payments/{payment_id}/status",
        params={"db": db_path},
        headers={"x-ae-secret": "testsecret"},
        json={"status": "captured"},
    )
    assert r2.status_code == 200

    evs = list_op_events(db_path, aggregate_type="payment", aggregate_id=payment_id, limit=50)
    topics = [e.topic for e in evs]
    assert "op.payment.authorized" in topics
    assert "op.payment.captured" in topics
    assert "op.payment.captured_direct" not in topics
    assert get_state(db_path, aggregate_type="payment", aggregate_id=payment_id) == "captured"
