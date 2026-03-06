import pytest

from ae import db, repo
from ae.enums import PaymentProvider, PaymentMethod, PaymentStatus, ReconciliationStatus
from ae.models import LeadIntake


def _mk_lead(db_path: str, *, booking_status: str = "confirmed", booking_value: float = 1500.0, booking_currency: str = "THB") -> int:
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
    return int(repo.insert_lead(db_path, lead))


def test_payment_create_creates_default_reconciliation(tmp_path):
    db_path = str(tmp_path / "ae.db")
    db.init_db(db_path)

    lead_id = _mk_lead(db_path, booking_status="confirmed")
    booking_id = f"lead-{lead_id}"

    repo.create_payment(
        db_path,
        payment_id="pay_rec_1",
        booking_id=booking_id,
        lead_id=lead_id,
        amount=123.0,
        currency="THB",
        provider=PaymentProvider.manual,
        method=PaymentMethod.cash,
        status=PaymentStatus.pending,
    )

    rec = repo.get_payment_reconciliation(db_path, "pay_rec_1")
    assert rec is not None
    assert rec.payment_id == "pay_rec_1"
    assert rec.status == ReconciliationStatus.unmatched
    assert rec.evidence_json.get("expected_amount") == 123.0
    assert rec.evidence_json.get("expected_currency") == "THB"


def test_upsert_reconciliation_and_list_join(tmp_path):
    db_path = str(tmp_path / "ae.db")
    db.init_db(db_path)

    lead_id = _mk_lead(db_path, booking_status="confirmed")
    booking_id = f"lead-{lead_id}"

    repo.create_payment(
        db_path,
        payment_id="pay_rec_2",
        booking_id=booking_id,
        lead_id=lead_id,
        amount=500.0,
        currency="THB",
        provider=PaymentProvider.manual,
        method=PaymentMethod.qr,
    )

    updated = repo.upsert_payment_reconciliation(
        db_path,
        payment_id="pay_rec_2",
        status=ReconciliationStatus.matched,
        matched_amount=500.0,
        matched_currency="THB",
        matched_ref="bank_tx_123",
        note="matched manually",
        updated_by="op:test",
        evidence_patch={"bank_statement_line": "L42"},
    )
    assert updated.status == ReconciliationStatus.matched
    assert updated.matched_ref == "bank_tx_123"
    assert updated.evidence_json.get("bank_statement_line") == "L42"

    joined = repo.list_payments_reconciliation(db_path, status=ReconciliationStatus.matched)
    assert len(joined) == 1
    assert joined[0]["payment"].payment_id == "pay_rec_2"
    assert joined[0]["reconciliation"].status == ReconciliationStatus.matched
