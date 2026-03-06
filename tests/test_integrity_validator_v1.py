from ae import db as dbmod
from ae.integrity_validator import run_integrity_check


def _insert_lead(con):
    # minimal lead_intake row
    con.execute(
        """INSERT INTO lead_intake (ts, source, page_id, client_id, name, phone, email, message, spam_score, meta_json)
             VALUES ('2026-01-01T00:00:00Z', 'meta', 'p1', 'c1', 'Test', '+100', 't@example.com', 'hi', 0, '{}')"""
    )
    return con.execute("SELECT MAX(lead_id) FROM lead_intake").fetchone()[0]


def test_integrity_validator_detects_op_state_pointer_issues(tmp_path):
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)
    con = dbmod.connect(db_path)
    with con:
        lead_id = _insert_lead(con)
        con.execute(
            """INSERT INTO op_states (aggregate_type, aggregate_id, state, updated_at, last_event_id, last_topic, last_occurred_at)
                 VALUES ('booking', ?, 'created', '2026-01-01T00:00:00Z', 'missing-event', 'op.booking.created', '2026-01-01T00:00:00Z')""",
            (f"lead-{lead_id}",),
        )

    report = run_integrity_check(db_path, emit_events=False)
    codes = {i.code for i in report.issues}
    assert report.status == "issues"
    assert "op_states.last_event_missing" in codes


def test_integrity_validator_detects_payment_booking_mismatch(tmp_path):
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)
    con = dbmod.connect(db_path)
    with con:
        lead_id = _insert_lead(con)
        con.execute(
            """INSERT INTO payments (payment_id, booking_id, lead_id, amount, currency, provider, method, status, external_ref, created_at, updated_at, meta_json)
                 VALUES ('pay1', 'wrong', ?, 10.0, 'USD', 'manual', 'cash', 'pending', NULL, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z', '{}')""",
            (lead_id,),
        )

    report = run_integrity_check(db_path, emit_events=False)
    codes = {i.code for i in report.issues}
    assert report.status == "issues"
    assert "payments.booking_id_mismatch" in codes
