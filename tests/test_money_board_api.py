"""API tests for Money Board endpoints."""

import os
from pathlib import Path
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from ae import db as dbmod, repo
from ae.repo_bookings import get_booking
from ae.console_app import app
from ae.models import Client, Customer, Booking, ServicePackage
from ae.service_booking import BookingService
from ae.enums import Trade


def _seed_money_board_test_data(db_path: str):
    """Seed client, customer, package, and bookings for money board tests."""
    dbmod.init_db(db_path)
    now = datetime.now(timezone.utc)
    
    repo.upsert_client(db_path, Client(
        client_id="mb_test",
        client_name="MB Test Client",
        trade=Trade.massage,
        geo_country="TH",
        geo_city="Bangkok",
        service_area=["Bangkok"],
        primary_phone="+66111111111",
        lead_email="mb@test.com",
    ))
    
    repo.create_package(db_path, ServicePackage(
        package_id="pkg_mb_test",
        client_id="mb_test",
        name="60 min Massage",
        price=1000.0,
        duration_min=60,
        addons=[],
        active=True,
        meta_json={},
        created_at=now,
        updated_at=now,
    ))
    
    repo.create_customer(db_path, Customer(
        customer_id="cust_mb_1",
        client_id="mb_test",
        display_name="Test Customer",
        phone="+66222222222",
        email="cust@test.com",
        created_at=now,
        updated_at=now,
    ))
    
    svc = BookingService(db_path)
    
    # Booking 1: NEW (minimal)
    b1 = svc.create_booking_for_customer(
        customer_id="cust_mb_1",
        client_id="mb_test",
        channel="web",
    )
    
    # Booking 2: TIME_WINDOW_SET (with package + time)
    b2 = svc.create_booking_for_customer(
        customer_id="cust_mb_1",
        client_id="mb_test",
        channel="telegram_bot",
        package_id="pkg_mb_test",
        preferred_time_window="Morning (9am-12pm)",
    )
    
    # Booking 3: CONFIRMED (need to confirm b2 first, then we'll have a confirmed one)
    svc.confirm_booking(b2.booking_id, actor_id="operator", override_reason="test")
    
    return b1.booking_id, b2.booking_id


def test_get_money_board_returns_four_columns(tmp_path):
    """GET /api/money-board returns columns with status in [pending, confirmed, complete, closed]."""
    os.environ.pop("AE_CONSOLE_SECRET", None)
    db_path = str(tmp_path / "acq.db")
    _seed_money_board_test_data(db_path)
    
    client = TestClient(app)
    r = client.get("/api/money-board", params={"db": db_path})
    assert r.status_code == 200
    data = r.json()
    assert "columns" in data
    col_statuses = [c["status"] for c in data["columns"]]
    assert set(col_statuses) == {"pending", "confirmed", "complete", "closed"}
    assert len(col_statuses) == 4


def test_get_money_board_items_in_correct_columns(tmp_path):
    """Create bookings with NEW, TIME_WINDOW_SET, CONFIRMED; assert they appear in correct columns."""
    os.environ.pop("AE_CONSOLE_SECRET", None)
    db_path = str(tmp_path / "acq.db")
    bk_new, bk_confirmed = _seed_money_board_test_data(db_path)
    
    client = TestClient(app)
    r = client.get("/api/money-board", params={"db": db_path})
    assert r.status_code == 200
    data = r.json()
    
    cols = {c["status"]: c for c in data["columns"]}
    pending_items = cols["pending"]["items"]
    confirmed_items = cols["confirmed"]["items"]
    
    pending_ids = [x["booking_id"] for x in pending_items]
    confirmed_ids = [x["booking_id"] for x in confirmed_items]
    
    assert bk_new in pending_ids
    assert bk_confirmed in confirmed_ids


def test_confirm_endpoint_transitions_to_confirmed(tmp_path):
    """Create TIME_WINDOW_SET booking, POST confirm, assert status CONFIRMED."""
    os.environ.pop("AE_CONSOLE_SECRET", None)
    db_path = str(tmp_path / "acq.db")
    _seed_money_board_test_data(db_path)
    
    # Create one more booking in TIME_WINDOW_SET for confirm test
    svc = BookingService(db_path)
    b = svc.create_booking_for_customer(
        customer_id="cust_mb_1",
        client_id="mb_test",
        channel="telegram_bot",
        package_id="pkg_mb_test",
        preferred_time_window="Afternoon (12pm-5pm)",
    )
    booking_id = b.booking_id
    
    client = TestClient(app)
    r = client.post(
        f"/api/money-board/{booking_id}/confirm",
        params={"db": db_path},
    )
    assert r.status_code == 200
    
    booking = get_booking(db_path, booking_id)
    assert booking.status == "CONFIRMED"


def test_set_package_on_pending_booking(tmp_path):
    """Create NEW booking, POST set-package, assert package updated."""
    os.environ.pop("AE_CONSOLE_SECRET", None)
    db_path = str(tmp_path / "acq.db")
    _seed_money_board_test_data(db_path)
    
    svc = BookingService(db_path)
    b = svc.create_booking_for_customer(
        customer_id="cust_mb_1",
        client_id="mb_test",
        channel="web",
    )
    booking_id = b.booking_id
    
    client = TestClient(app)
    r = client.post(
        f"/api/money-board/{booking_id}/set-package",
        params={"db": db_path},
        json={"package_id": "pkg_mb_test"},
    )
    assert r.status_code == 200
    
    booking = get_booking(db_path, booking_id)
    assert booking.package_id == "pkg_mb_test"
    assert booking.status == "PACKAGE_SELECTED"


def test_set_time_window_on_pending_booking(tmp_path):
    """Create PACKAGE_SELECTED booking, POST set-time-window, assert preferred_time_window updated."""
    os.environ.pop("AE_CONSOLE_SECRET", None)
    db_path = str(tmp_path / "acq.db")
    _seed_money_board_test_data(db_path)
    
    svc = BookingService(db_path)
    b = svc.create_booking_for_customer(
        customer_id="cust_mb_1",
        client_id="mb_test",
        channel="web",
        package_id="pkg_mb_test",
    )
    booking_id = b.booking_id
    
    client = TestClient(app)
    r = client.post(
        f"/api/money-board/{booking_id}/set-time-window",
        params={"db": db_path},
        json={"preferred_window": "Evening (5pm-9pm)"},
    )
    assert r.status_code == 200
    
    booking = get_booking(db_path, booking_id)
    assert booking.preferred_time_window == "Evening (5pm-9pm)"
    assert booking.status == "TIME_WINDOW_SET"


def test_request_deposit_on_pending_booking(tmp_path):
    """Create TIME_WINDOW_SET booking, POST request-deposit, assert DEPOSIT_REQUESTED."""
    os.environ.pop("AE_CONSOLE_SECRET", None)
    db_path = str(tmp_path / "acq.db")
    _seed_money_board_test_data(db_path)
    
    svc = BookingService(db_path)
    b = svc.create_booking_for_customer(
        customer_id="cust_mb_1",
        client_id="mb_test",
        channel="telegram_bot",
        package_id="pkg_mb_test",
        preferred_time_window="Morning (9am-12pm)",
    )
    booking_id = b.booking_id
    
    client = TestClient(app)
    r = client.post(
        f"/api/money-board/{booking_id}/request-deposit",
        params={"db": db_path},
        json={"amount": 500, "method": "promptpay", "payment_link": "https://pay.example.com/123"},
    )
    assert r.status_code == 200
    
    booking = get_booking(db_path, booking_id)
    assert booking.status == "DEPOSIT_REQUESTED"
    assert booking.deposit_amount == 500


def test_mark_paid_on_deposit_requested(tmp_path):
    """Create DEPOSIT_REQUESTED booking, POST mark-paid, assert CONFIRMED."""
    os.environ.pop("AE_CONSOLE_SECRET", None)
    db_path = str(tmp_path / "acq.db")
    _seed_money_board_test_data(db_path)
    
    svc = BookingService(db_path)
    b = svc.create_booking_for_customer(
        customer_id="cust_mb_1",
        client_id="mb_test",
        channel="telegram_bot",
        package_id="pkg_mb_test",
        preferred_time_window="Afternoon (12pm-5pm)",
    )
    svc.request_deposit(b.booking_id, 300, "https://pay.example.com/456", "operator")
    
    client = TestClient(app)
    r = client.post(
        f"/api/money-board/{b.booking_id}/mark-paid",
        params={"db": db_path},
    )
    assert r.status_code == 200
    
    booking = get_booking(db_path, b.booking_id)
    assert booking.status == "CONFIRMED"
    assert booking.deposit_status == "paid"
