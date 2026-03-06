import sys
import os
from datetime import datetime, timezone
import json

# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo
from ae.models import LeadIntake, BookingRequest

def create_test_data():
    db_path = "acq.db"
    
    # 1. Create a lead with name and phone
    print("Creating test lead...")
    now = datetime.now(timezone.utc).isoformat()
    lead = LeadIntake(
        lead_id=0, # Auto-increment
        ts=now,
        source="manual_test",
        page_id="p1",
        client_id="demo1",
        name="Test Customer John",
        phone="0812345678",
        email="john@example.com",
        message="Interested in massage",
        status="new",
        meta_json={"test": True}
    )
    lead_id = repo.insert_lead(db_path, lead)
    print(f"Created Lead ID: {lead_id}")
    
    # 2. Create a booking request for this lead
    print("Creating booking request...")
    request_id = f"br_test_{lead_id}"
    booking = BookingRequest(
        request_id=request_id,
        lead_id=lead_id,
        package_id="pkg-demo1-relax-60",
        status="requested",
        preferred_window="Morning (9am-12pm)",
        meta_json={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    repo.create_booking_request(db_path, booking)
    
    # Update lead status to match
    repo.update_lead_outcome(db_path, lead_id, status="package_selected") # or whatever logic updates lead status
    
    print(f"Created Booking Request: {request_id}")
    
if __name__ == "__main__":
    create_test_data()
