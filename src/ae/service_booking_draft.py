from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import uuid

from . import repo
from .models import Booking, Customer
from .repo_bookings import create_booking, update_booking_status, get_customer, create_customer

class BookingService:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def create_lead_booking(self, client_id: str, lead_data: Dict[str, Any]) -> str:
        """
        Create a new booking and customer from raw lead data.
        Transitions: -> NEW
        """
        # 1. Create/Find Customer
        customer_id = f"cust_{uuid.uuid4().hex[:12]}"
        
        # Try to find existing customer by phone or email if available?
        # For v1, we'll just create a new one or simplistic check could go here.
        # But let's stick to the plan: deduplication later. 
        # Actually, let's do a simple loose check if phone exists?
        # For now, simplistic creation.
        
        c = Customer(
            customer_id=customer_id,
            client_id=client_id,
            display_name=lead_data.get("name") or "Visitor",
            phone=lead_data.get("phone"),
            email=lead_data.get("email"),
            telegram_username=lead_data.get("telegram_username"),
            telegram_id=str(lead_data.get("telegram_id")) if lead_data.get("telegram_id") else None,
            created_at=self._now(),
            updated_at=self._now()
        )
        create_customer(self.db_path, c)

        # 2. Create Booking
        booking_id = f"bk_{uuid.uuid4().hex[:12]}"
        b = Booking(
            booking_id=booking_id,
            client_id=client_id,
            customer_id=customer_id,
            lead_id=lead_data.get("lead_id"),
            channel="web", # logic to determine channel
            status="NEW",
            package_id="none",
            package_name_snapshot="—",
            price_amount=0,
            currency="THB",
            duration_minutes=0,
            created_at=self._now(),
            updated_at=self._now()
        )
        create_booking(self.db_path, b)
        
        # Log creation event? create_booking doesn't autosupport creation event yet,
        # but the next state change will.
        # Let's verify if we want an event for CREATED.
        # repo.log_event(...) # if we exposed it. 
        # For now, NEW is the start state.
        
        return booking_id

    def set_package(self, booking_id: str, package_id: str, actor_id: str):
        """
        Transitions: NEW -> PACKAGE_SELECTED
        """
        # Get booking (we need a get_booking in repo, missing!)
        # Waiting for that... let's assume we add it or use SQL directly here? 
        # Better to add `get_booking` to repo.
        pass 
        # ... holding off implementation until I add get_booking to repo.

    # ... I realize I missed `get_booking` in `repo_bookings.py`. 
    # I should add it first.

