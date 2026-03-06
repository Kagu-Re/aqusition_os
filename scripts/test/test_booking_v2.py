import sys
import os
from datetime import datetime, timezone
import json

# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo
from ae.models import Booking, Customer

def test_booking_flow():
    db_path = "d:/aqusition_os/acq.db"
    
    print("Creating customer...")
    cid = f"cust_{int(datetime.now().timestamp())}"
    cust = Customer(
        customer_id=cid,
        client_id="test-client",
        display_name="Test Customer V2",
        phone="0812345678",
        email="testv2@example.com",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    repo.create_customer(db_path, cust)
    print(f"Customer created: {cid}")
    
    print("Creating booking...")
    bid = f"bk_{int(datetime.now().timestamp())}"
    booking = Booking(
        booking_id=bid,
        client_id="test-client",
        customer_id=cid,
        channel="web",
        status="NEW",
        package_id="pkg-test",
        package_name_snapshot="Test Package",
        price_amount=1000.0,
        currency="THB",
        duration_minutes=60,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    repo.create_booking(db_path, booking)
    print(f"Booking created: {bid}")
    
    print("Updating status...")
    repo.update_booking_status(db_path, bid, "CONFIRMED", "operator", "op-1", "deposit received")
    
    print("Fetching Board...")
    items = repo.get_money_board_bookings(db_path, "test-client")
    found = next((i for i in items if i['booking_id'] == bid), None)
    
    if found:
        print(f"[SUCCESS] Found booking on board: {found['status']}")
        print(f"Customer Name: {found['display_name']}")
    else:
        print("[FAIL] Booking not found on board")

if __name__ == "__main__":
    test_booking_flow()
