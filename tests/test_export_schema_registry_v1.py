from ae import db as dbmod
from ae.export_engine import run_export, resolve_schema


def _insert_lead(con, *, booking_status: str = "none"):
    con.execute(
        """INSERT INTO lead_intake (
            ts, source, page_id, client_id, name, phone, email, message,
            spam_score, is_spam, status, booking_status, booking_value, booking_currency, booking_ts, meta_json
        ) VALUES (
            '2026-01-01T00:00:00Z', 'web', 'p1', 'c1', 'Test', '+100', 't@example.com', 'hi',
            0, 0, 'new', ?, 100.0, 'THB', '2026-01-02T00:00:00Z', '{}'
        )""",
        (booking_status,),
    )
    return con.execute("SELECT MAX(lead_id) FROM lead_intake").fetchone()[0]


def test_export_registry_resolves_schema(tmp_path):
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)
    s = resolve_schema(db_path, "leads_basic")
    assert s.name == "leads_basic"
    assert len(s.fields) > 0


def test_run_export_leads_and_bookings(tmp_path):
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)
    con = dbmod.connect(db_path)
    with con:
        _insert_lead(con, booking_status="none")
        _insert_lead(con, booking_status="confirmed")

    leads = run_export(db_path, "leads_basic", limit=10)
    assert len(leads) == 2
    assert set(leads[0].keys()) >= {"lead_id", "email", "status"}

    bookings = run_export(db_path, "bookings_basic", limit=10)
    assert len(bookings) == 1
    assert bookings[0]["booking_status"] == "confirmed"


def test_run_export_payments(tmp_path):
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)
    con = dbmod.connect(db_path)
    with con:
        lead_id = _insert_lead(con, booking_status="confirmed")
        con.execute(
            """INSERT INTO payments (
                payment_id, booking_id, lead_id, amount, currency, provider, method, status,
                external_ref, created_at, updated_at, meta_json
            ) VALUES (
                'pay1', ?, ?, 200.0, 'THB', 'manual', 'cash', 'pending',
                NULL, '2026-01-03T00:00:00Z', '2026-01-03T00:00:00Z', '{}'
            )""",
            (f"lead-{lead_id}", lead_id),
        )

    rows = run_export(db_path, "payments_basic", limit=10)
    assert len(rows) == 1
    assert rows[0]["lead_id"] == lead_id
    assert rows[0]["amount"] == 200.0
