import os
from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod, repo
from ae.models import Client, LeadIntake, ServicePackage, BookingRequest, PaymentIntent
from ae.enums import Trade, PaymentStatus
from datetime import datetime


def _seed(db_path: str):
    """Seed database with test data."""
    dbmod.init_db(db_path)
    # Create client
    repo.upsert_client(db_path, Client(
        client_id="c1",
        client_name="Client One",
        trade=Trade.plumber,
        geo_country="th",
        geo_city="chiang_mai",
        service_area=["CM"],
        primary_phone="000",
        lead_email="a@example.com",
        status="live",
        hours=None,
        license_badges=[],
        price_anchor=None,
        brand_theme=None,
        notes_internal=None,
    ))
    # Create package
    now = datetime.utcnow()
    pkg = ServicePackage(
        package_id="pkg1",
        client_id="c1",
        name="60 min session",
        price=800.0,
        duration_min=60,
        addons=[],
        active=True,
        meta_json={},
        created_at=now,
        updated_at=now,
    )
    repo.create_package(db_path, pkg)
    # Create lead
    lead = LeadIntake(
        ts=now.isoformat() + "Z",
        source="test",
        name="Test User",
        phone="+66-80-123-4567",
        status="new",
        booking_status="none",
        meta_json={},
    )
    repo.insert_lead(db_path, lead)
    # Create booking request
    leads = repo.list_leads(db_path, limit=1)
    lead_id = leads[0].lead_id
    br = BookingRequest(
        request_id="br1",
        lead_id=lead_id,
        package_id="pkg1",
        status="deposit_requested",
        meta_json={},
        created_at=now,
        updated_at=now,
    )
    repo.create_booking_request(db_path, br)


def test_payment_intent_create_and_get(tmp_path):
    """Test creating and retrieving a payment intent."""
    db_path = str(tmp_path / "t.db")
    _seed(db_path)
    os.environ.pop("AE_CONSOLE_SECRET", None)
    client = TestClient(app)

    # Get lead_id and booking_request_id
    leads = repo.list_leads(db_path, limit=1)
    lead_id = leads[0].lead_id

    # Create payment intent
    r = client.post("/api/payment-intents?db=" + db_path, json={
        "intent_id": "pi1",
        "lead_id": lead_id,
        "booking_request_id": "br1",
        "amount": 800.0,
        "method": "promptpay",
        "payment_link": "https://example.com/pay",
        "meta_json": {}
    })
    assert r.status_code == 200
    body = r.json()
    assert body["intent"]["intent_id"] == "pi1"
    assert body["intent"]["amount"] == 800.0
    assert body["intent"]["status"] == "requested"

    # Get payment intent
    r2 = client.get("/api/payment-intents/pi1?db=" + db_path)
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["intent"]["intent_id"] == "pi1"


def test_payment_intent_list_with_filters(tmp_path):
    """Test listing payment intents with filters."""
    db_path = str(tmp_path / "t.db")
    _seed(db_path)
    os.environ.pop("AE_CONSOLE_SECRET", None)
    client = TestClient(app)

    # Get lead_id
    leads = repo.list_leads(db_path, limit=1)
    lead_id = leads[0].lead_id

    # Create multiple payment intents
    now = datetime.utcnow()
    pi1 = PaymentIntent(
        intent_id="pi1",
        lead_id=lead_id,
        booking_request_id="br1",
        amount=800.0,
        method="promptpay",
        status="requested",
        meta_json={},
        created_at=now,
        updated_at=now,
    )
    pi2 = PaymentIntent(
        intent_id="pi2",
        lead_id=lead_id,
        booking_request_id="br1",
        amount=1200.0,
        method="stripe",
        status="paid",
        meta_json={},
        created_at=now,
        updated_at=now,
    )
    repo.create_payment_intent(db_path, pi1)
    repo.create_payment_intent(db_path, pi2)

    # List all
    r = client.get("/api/payment-intents?db=" + db_path)
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 2

    # List by status
    r2 = client.get("/api/payment-intents?db=" + db_path + "&status=paid")
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["count"] >= 1
    assert body2["items"][0]["status"] == "paid"

    # List by booking_request_id
    r3 = client.get("/api/payment-intents?db=" + db_path + "&booking_request_id=br1")
    assert r3.status_code == 200
    body3 = r3.json()
    assert body3["count"] >= 2


def test_payment_intent_mark_paid_integration(tmp_path):
    """Test marking payment intent as paid creates Payment and updates BookingRequest."""
    db_path = str(tmp_path / "t.db")
    _seed(db_path)
    os.environ.pop("AE_CONSOLE_SECRET", None)
    client = TestClient(app)

    # Get lead_id
    leads = repo.list_leads(db_path, limit=1)
    lead_id = leads[0].lead_id

    # Create payment intent
    now = datetime.utcnow()
    pi = PaymentIntent(
        intent_id="pi1",
        lead_id=lead_id,
        booking_request_id="br1",
        amount=800.0,
        method="promptpay",
        status="requested",
        meta_json={},
        created_at=now,
        updated_at=now,
    )
    repo.create_payment_intent(db_path, pi)

    # Mark as paid
    r = client.put("/api/payment-intents/pi1/mark-paid?db=" + db_path)
    assert r.status_code == 200
    body = r.json()
    assert body["intent"]["status"] == "paid"

    # Verify Payment was created (using lead-based booking_id format)
    payments = repo.list_payments(db_path, booking_id=f"lead-{lead_id}", limit=10)
    assert len(payments) >= 1
    payment = payments[0]
    assert payment.amount == 800.0
    assert payment.status == PaymentStatus.captured
    assert payment.meta_json.get("booking_request_id") == "br1"

    # Verify BookingRequest status updated to confirmed
    booking = repo.get_booking_request(db_path, "br1")
    assert booking is not None
    assert booking.status == "confirmed"


def test_payment_intent_state_machine_enforcement(tmp_path):
    """Test that state machine enforces transitions."""
    db_path = str(tmp_path / "t.db")
    _seed(db_path)

    # Get lead_id
    leads = repo.list_leads(db_path, limit=1)
    lead_id = leads[0].lead_id

    # Create payment intent
    now = datetime.utcnow()
    pi = PaymentIntent(
        intent_id="pi1",
        lead_id=lead_id,
        booking_request_id="br1",
        amount=800.0,
        method="promptpay",
        status="requested",
        meta_json={},
        created_at=now,
        updated_at=now,
    )
    repo.create_payment_intent(db_path, pi)

    # Mark as paid (valid transition)
    updated = repo.mark_payment_intent_paid(db_path, "pi1")
    assert updated is not None
    assert updated.status == "paid"

    # Try to mark as paid again (should be idempotent)
    updated2 = repo.mark_payment_intent_paid(db_path, "pi1")
    assert updated2 is not None
    assert updated2.status == "paid"


def test_payment_intent_repository_crud(tmp_path):
    """Test repository functions directly."""
    db_path = str(tmp_path / "t.db")
    _seed(db_path)

    # Get lead_id
    leads = repo.list_leads(db_path, limit=1)
    lead_id = leads[0].lead_id

    now = datetime.utcnow()
    pi = PaymentIntent(
        intent_id="pi1",
        lead_id=lead_id,
        booking_request_id="br1",
        amount=800.0,
        method="promptpay",
        status="requested",
        payment_link="https://example.com/pay",
        meta_json={"note": "test"},
        created_at=now,
        updated_at=now,
    )

    # Create
    created = repo.create_payment_intent(db_path, pi)
    assert created.intent_id == "pi1"
    assert created.amount == 800.0
    assert created.status == "requested"

    # Get
    retrieved = repo.get_payment_intent(db_path, "pi1")
    assert retrieved is not None
    assert retrieved.lead_id == lead_id
    assert retrieved.booking_request_id == "br1"

    # List
    all_intents = repo.list_payment_intents(db_path, booking_request_id="br1")
    assert len(all_intents) >= 1

    # List by status
    requested_intents = repo.list_payment_intents(db_path, status="requested")
    assert len(requested_intents) >= 1
