from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import uuid

from . import repo
from .models import Booking, Customer
from .repo_bookings import (
    create_booking, update_booking_status, update_booking_fields,
    get_customer, create_customer, get_booking
)

class TransitionError(Exception):
    pass

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
        # ID generation
        customer_id = f"cust_{uuid.uuid4().hex[:12]}"
        booking_id = f"bk_{uuid.uuid4().hex[:12]}"
        
        # 1. Create Customer
        # Basic name resolution logic
        name = lead_data.get("name")
        if not name:
            if lead_data.get("telegram_username"):
                name = f"@{lead_data.get('telegram_username')}"
            else:
                name = "Visitor"

        c = Customer(
            customer_id=customer_id,
            client_id=client_id,
            display_name=name,
            phone=lead_data.get("phone"),
            email=lead_data.get("email"),
            telegram_username=lead_data.get("telegram_username"),
            telegram_id=str(lead_data.get("telegram_id")) if lead_data.get("telegram_id") else None,
            created_at=self._now(),
            updated_at=self._now()
        )
        create_customer(self.db_path, c)

        # 2. Create Booking
        b = Booking(
            booking_id=booking_id,
            client_id=client_id,
            customer_id=customer_id,
            lead_id=lead_data.get("lead_id"),
            channel=lead_data.get("source") or "web",
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
        return booking_id

    def create_booking_for_customer(
        self,
        customer_id: str,
        client_id: str,
        channel: str = "web",
        *,
        package_id: Optional[str] = None,
        preferred_time_window: Optional[str] = None,
        lead_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Booking:
        """
        Create a new booking for an existing customer.
        When package_id is provided, creates a full booking with package details.
        Transitions: -> NEW (minimal) or -> TIME_WINDOW_SET (with package + window)
        Returns: the created Booking object.
        """
        booking_id = f"bk_{uuid.uuid4().hex[:12]}"
        now = self._now()

        if package_id:
            pkg = repo.get_package(self.db_path, package_id)
            if not pkg:
                raise ValueError(f"Package {package_id} not found")
            status = "TIME_WINDOW_SET" if preferred_time_window else "PACKAGE_SELECTED"
            b = Booking(
                booking_id=booking_id,
                client_id=client_id,
                customer_id=customer_id,
                lead_id=lead_id,
                channel=channel,
                status=status,
                package_id=pkg.package_id,
                package_name_snapshot=pkg.name,
                price_amount=pkg.price,
                currency="THB",
                duration_minutes=pkg.duration_min,
                preferred_time_window=preferred_time_window,
                created_at=now,
                updated_at=now,
            )
        else:
            b = Booking(
                booking_id=booking_id,
                client_id=client_id,
                customer_id=customer_id,
                lead_id=lead_id,
                channel=channel,
                status="NEW",
                package_id="none",
                package_name_snapshot="—",
                price_amount=0,
                currency="THB",
                duration_minutes=0,
                created_at=now,
                updated_at=now,
            )

        create_booking(self.db_path, b)
        return b

    def set_package(self, booking_id: str, package_id: str, actor_id: str):
        """
        Transitions: NEW -> PACKAGE_SELECTED
        """
        booking = get_booking(self.db_path, booking_id)
        if not booking:
            raise ValueError("Booking not found")

        # Get package details
        # We need to fetch package from repo (standard repo)
        from . import repo # lazy import to avoid circle if any
        pkg = repo.get_package(self.db_path, package_id)
        if not pkg:
            raise ValueError("Package not found")

        # Update Booking fields
        updates = {
            "package_id": pkg.package_id,
            "package_name_snapshot": pkg.name,
            "price_amount": pkg.price,
            "duration_minutes": pkg.duration_min
        }
        update_booking_fields(self.db_path, booking_id, updates, "operator", actor_id)

        # Transition if in NEW
        if booking.status == "NEW":
            update_booking_status(self.db_path, booking_id, "PACKAGE_SELECTED", "operator", actor_id)

    def set_time_window(self, booking_id: str, window: str, actor_id: str):
        """
        Transitions: PACKAGE_SELECTED -> TIME_WINDOW_SET
        """
        booking = get_booking(self.db_path, booking_id)
        if not booking:
            raise ValueError("Booking not found")
            
        update_booking_fields(self.db_path, booking_id, {"preferred_time_window": window}, "operator", actor_id)
        
        # Transition logic
        if booking.status == "PACKAGE_SELECTED":
             update_booking_status(self.db_path, booking_id, "TIME_WINDOW_SET", "operator", actor_id)
        elif booking.status == "NEW":
             # If they set time window before package (unlikely but possible), 
             # we might stay in NEW or go to partial state? 
             # For now, strict: must have package to move forward.
             if booking.package_id != "none":
                 update_booking_status(self.db_path, booking_id, "TIME_WINDOW_SET", "operator", actor_id)

    def request_deposit(self, booking_id: str, amount: float, link: str, actor_id: str):
        """
        Transitions: TIME_WINDOW_SET -> DEPOSIT_REQUESTED
        """
        booking = get_booking(self.db_path, booking_id)
        if not booking:
            raise ValueError("Booking not found")
            
        # Update deposit fields
        updates = {
            "deposit_required": 1,
            "deposit_amount": amount,
            "deposit_status": "requested",
            "payment_link": link
        }
        update_booking_fields(self.db_path, booking_id, updates, "operator", actor_id)
        
        update_booking_status(self.db_path, booking_id, "DEPOSIT_REQUESTED", "operator", actor_id)

    def mark_deposit_paid(self, booking_id: str, ref: str, actor_id: str):
        """
        Transitions: DEPOSIT_REQUESTED -> CONFIRMED
        """
        booking = get_booking(self.db_path, booking_id)
        if not booking:
             raise ValueError("Booking not found")
             
        updates = {
            "deposit_status": "paid",
            "payment_ref": ref
        }
        update_booking_fields(self.db_path, booking_id, updates, "operator", actor_id)
        
        update_booking_status(self.db_path, booking_id, "CONFIRMED", "operator", actor_id, reason="deposit_paid")

    def confirm_booking(self, booking_id: str, actor_id: str, override_reason: str = None):
        """
        Transitions: TIME_WINDOW_SET -> CONFIRMED (if no deposit)
        OR DEPOSIT_REQUESTED -> CONFIRMED (requires override if not paid)
        """
        booking = get_booking(self.db_path, booking_id)
        
        if booking.status == "DEPOSIT_REQUESTED" and booking.deposit_status != "paid" and not override_reason:
            raise TransitionError("Cannot confirm unpaid booking without override reason")
            
        update_booking_status(self.db_path, booking_id, "CONFIRMED", "operator", actor_id, reason=override_reason)

    def mark_complete(self, booking_id: str, actor_id: str):
        """
        Transitions: CONFIRMED -> COMPLETE
        """
        update_booking_status(self.db_path, booking_id, "COMPLETE", "operator", actor_id)

    def close_booking(self, booking_id: str, actor_id: str):
        """
        Transitions: COMPLETE -> CLOSED
        """
        update_booking_status(self.db_path, booking_id, "CLOSED", "operator", actor_id)

    def cancel_booking(self, booking_id: str, actor_id: str, reason: str = None):
        """
        Transitions: ANY -> CANCELLED
        """
        update_booking_status(self.db_path, booking_id, "CANCELLED", "operator", actor_id, reason=reason)
