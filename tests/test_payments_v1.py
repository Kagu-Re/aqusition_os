import pytest

from ae import db, repo
from ae.enums import PaymentProvider, PaymentMethod, PaymentStatus
from ae.models import LeadIntake


def _mk_lead(db_path: str, lead_id: int, *, booking_status: str = "confirmed", booking_value: float = 1500.0, booking_currency: str = "THB"):
    # Insert a lead record with booking fields so payments can bind.
    lead = LeadIntake(
        ts="2026-01-01T00:00:00",
        source="test",
        name="Test",
        phone="000",
        status="new",
        booking_status=booking_status,
        booking_value=booking_value,
        booking_currency=booking_currency,
        booking_ts="2026-01-01T00:00:00",
        meta_json={},
    )
    inserted = repo.insert_lead(db_path, lead)
    # repo.insert_lead returns id; we want deterministic ids for tests, so assert and overwrite if needed
    assert int(inserted) >= 1
    # SQLite AUTOINCREMENT can't be forced easily; we return the inserted id
    return int(inserted)


def test_payment_create_and_get(tmp_path):
    db_path = str(tmp_path / "ae.db")
    db.init_db(db_path)

    lead_id = _mk_lead(db_path, 123, booking_status="confirmed", booking_value=1500.0, booking_currency="THB")
    booking_id = f"lead-{lead_id}"

    p = repo.create_payment(
        db_path,
        payment_id="pay_1",
        booking_id=booking_id,
        lead_id=lead_id,
        amount=1500.0,
        currency="THB",
        provider=PaymentProvider.manual,
        method=PaymentMethod.cash,
        status=PaymentStatus.pending,
        external_ref=None,
        meta_json={"note": "test"},
    )

    got = repo.get_payment(db_path, "pay_1")
    assert got is not None
    assert got.payment_id == "pay_1"
    assert got.booking_id == booking_id
    assert got.amount == 1500.0
    assert got.meta_json.get("note") == "test"


def test_payment_registry_enforces_provider_method(tmp_path):
    db_path = str(tmp_path / "ae.db")
    db.init_db(db_path)

    lead_id = _mk_lead(db_path, 1, booking_status="confirmed")
    booking_id = f"lead-{lead_id}"

    with pytest.raises(ValueError):
        repo.create_payment(
            db_path,
            payment_id="pay_bad",
            booking_id=booking_id,
            lead_id=lead_id,
            amount=1.0,
            provider=PaymentProvider.stripe,
            method=PaymentMethod.cash,  # not allowed for stripe
        )


def test_payment_registry_enforces_external_ref(tmp_path):
    db_path = str(tmp_path / "ae.db")
    db.init_db(db_path)

    lead_id = _mk_lead(db_path, 2, booking_status="confirmed")
    booking_id = f"lead-{lead_id}"

    with pytest.raises(ValueError):
        repo.create_payment(
            db_path,
            payment_id="pay_bad2",
            booking_id=booking_id,
            lead_id=lead_id,
            amount=1.0,
            provider=PaymentProvider.stripe,
            method=PaymentMethod.card,
            external_ref=None,  # required
        )


def test_payment_update_status_and_list(tmp_path):
    db_path = str(tmp_path / "ae.db")
    db.init_db(db_path)

    lead_id1 = _mk_lead(db_path, 200, booking_status="confirmed")
    booking_id1 = f"lead-{lead_id1}"
    lead_id2 = _mk_lead(db_path, 201, booking_status="confirmed")
    booking_id2 = f"lead-{lead_id2}"

    repo.create_payment(
        db_path,
        payment_id="pay_2",
        booking_id=booking_id1,
        lead_id=lead_id1,
        amount=999.0,
        provider=PaymentProvider.manual,
        method=PaymentMethod.qr,
    )

    updated = repo.update_payment_status(
        db_path, payment_id="pay_2", status=PaymentStatus.captured, meta_patch={"captured_by": "operator"}
    )
    assert updated is not None
    assert updated.status == PaymentStatus.captured
    assert updated.meta_json.get("captured_by") == "operator"

    items = repo.list_payments(db_path, booking_id=booking_id1)
    assert len(items) == 1
    assert items[0].payment_id == "pay_2"


def test_payment_binding_rejects_mismatched_booking_id(tmp_path):
    db_path = str(tmp_path / "ae.db")
    db.init_db(db_path)
    lead_id = _mk_lead(db_path, 10, booking_status="confirmed")
    with pytest.raises(ValueError):
        repo.create_payment(
            db_path,
            payment_id="pay_bad_bind",
            booking_id="lead-999",
            lead_id=lead_id,
            amount=10.0,
            currency="THB",
            provider=PaymentProvider.manual,
            method=PaymentMethod.cash,
        )


def test_payment_binding_rejects_cancelled_booking(tmp_path):
    db_path = str(tmp_path / "ae.db")
    db.init_db(db_path)
    lead_id = _mk_lead(db_path, 11, booking_status="cancelled")
    booking_id = f"lead-{lead_id}"
    with pytest.raises(ValueError):
        repo.create_payment(
            db_path,
            payment_id="pay_bad_cancel",
            booking_id=booking_id,
            lead_id=lead_id,
            amount=10.0,
            currency="THB",
            provider=PaymentProvider.manual,
            method=PaymentMethod.cash,
        )


def test_payment_status_capture_requires_confirmed(tmp_path):
    db_path = str(tmp_path / "ae.db")
    db.init_db(db_path)
    lead_id = _mk_lead(db_path, 12, booking_status="booked")
    booking_id = f"lead-{lead_id}"
    repo.create_payment(
        db_path,
        payment_id="pay_cap",
        booking_id=booking_id,
        lead_id=lead_id,
        amount=10.0,
        currency="THB",
        provider=PaymentProvider.manual,
        method=PaymentMethod.cash,
        status=PaymentStatus.pending,
    )
    with pytest.raises(ValueError):
        repo.update_payment_status(db_path, payment_id="pay_cap", status=PaymentStatus.captured)

