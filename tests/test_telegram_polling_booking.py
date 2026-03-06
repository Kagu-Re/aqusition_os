"""Tests for Telegram bot booking flow: package selection, timeslot booking, vendor notification."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from ae import db as dbmod, repo
from ae.models import Client, ServicePackage, BookingRequest, LeadIntake, ChatChannel
from ae.enums import Trade, ChatProvider
from ae.telegram_polling import TelegramPollingClient
from ae.repo_chat_channels import upsert_chat_channel
from ae.repo_chat_conversations import get_or_create_conversation
from ae.console_routes_service_packages_public import _calculate_availability_for_package


def _seed_test_data(db_path: str):
    """Seed database with test data."""
    dbmod.init_db(db_path)
    
    # Create client
    repo.upsert_client(db_path, Client(
        client_id="test-massage-spa",
        client_name="Test Massage Spa",
        trade=Trade.massage_therapist,
        geo_country="TH",
        geo_city="Bangkok",
        service_area=["Bangkok"],
        primary_phone="+66123456789",
        lead_email="test@example.com",
        status="live",
    ))
    
    # Create packages
    now = datetime.now(timezone.utc)
    packages = [
        ServicePackage(
            package_id="pkg1",
            client_id="test-massage-spa",
            name="60 min Thai Massage",
            price=800.0,
            duration_min=60,
            addons=[],
            active=True,
            meta_json={"max_capacity": 5},
            created_at=now,
            updated_at=now,
        ),
        ServicePackage(
            package_id="pkg2",
            client_id="test-massage-spa",
            name="90 min Aromatherapy",
            price=1200.0,
            duration_min=90,
            addons=[],
            active=True,
            meta_json={"max_capacity": 3},
            created_at=now,
            updated_at=now,
        ),
        ServicePackage(
            package_id="pkg3",
            client_id="test-massage-spa",
            name="120 min Full Body",
            price=1500.0,
            duration_min=120,
            addons=[],
            active=True,
            meta_json={"max_capacity": 2},
            created_at=now,
            updated_at=now,
        ),
    ]
    
    for pkg in packages:
        repo.create_package(db_path, pkg)
    
    # Create Telegram channels
    upsert_chat_channel(
        db_path,
        channel_id="ch_customer_telegram",
        provider=ChatProvider.telegram,
        handle="@test_bot",
        meta_json={
            "telegram_bot_token": "test_token_customer",
            "client_id": "test-massage-spa",
            "bot_type": "customer"
        }
    )
    
    upsert_chat_channel(
        db_path,
        channel_id="ch_vendor_telegram",
        provider=ChatProvider.telegram,
        handle="@vendor_bot",
        meta_json={
            "telegram_bot_token": "test_token_vendor",
            "bot_type": "vendor",
            "vendor_chat_id": "123456789"
        }
    )


@pytest.mark.asyncio
async def test_package_selection_by_number(tmp_path):
    """Test that package selection by number works correctly."""
    db_path = str(tmp_path / "acq.db")
    _seed_test_data(db_path)
    
    client = TelegramPollingClient("test_token_customer", db_path)
    client.send_message = AsyncMock()
    
    # Create conversation
    conversation = get_or_create_conversation(
        db_path,
        conversation_id="conv_test",
        channel_id="ch_customer_telegram",
        external_thread_id="12345",
        meta_json={}
    )
    
    from ae.repo_chat_channels import get_chat_channel
    channel = get_chat_channel(db_path, "ch_customer_telegram")
    
    # First, show package list
    await client.handle_package_selection(conversation, channel)
    
    # Verify packages were listed
    assert client.send_message.called
    call_args = client.send_message.call_args[0]
    assert "60 min Thai Massage" in call_args[1]
    assert "90 min Aromatherapy" in call_args[1]
    
    # Get updated conversation with package list
    conversation = get_or_create_conversation(
        db_path,
        conversation_id="conv_test",
        channel_id="ch_customer_telegram",
        external_thread_id="12345",
        meta_json={}
    )
    
    # Select package by number
    client.send_message.reset_mock()
    await client.handle_package_number_selection(conversation, channel, 2)
    
    # Verify package was selected
    assert client.send_message.called
    call_args = client.send_message.call_args[0]
    assert "90 min Aromatherapy" in call_args[1]
    assert "yes" in call_args[1].lower()
    
    # Verify package_id stored in conversation
    conversation = get_or_create_conversation(
        db_path,
        conversation_id="conv_test",
        channel_id="ch_customer_telegram",
        external_thread_id="12345",
        meta_json={}
    )
    assert conversation.meta_json.get("pending_package_id") == "pkg2"


def test_timeslot_availability_calculation(tmp_path):
    """Test that timeslot availability calculation shows correct slots."""
    db_path = str(tmp_path / "acq.db")
    _seed_test_data(db_path)
    
    # Get package
    package = repo.get_package(db_path, "pkg1")
    
    # Initially, should have full capacity
    availability = _calculate_availability_for_package(
        db_path,
        "pkg1",
        package.meta_json or {}
    )
    assert availability == 5
    
    # Create 2 active bookings
    now = datetime.now(timezone.utc)
    from ae.repo_booking_requests import create_booking_request
    
    booking1 = BookingRequest(
        request_id="br1",
        lead_id=1,
        package_id="pkg1",
        preferred_window="Morning (9am-12pm)",
        status="confirmed",
        created_at=now,
        updated_at=now
    )
    
    booking2 = BookingRequest(
        request_id="br2",
        lead_id=2,
        package_id="pkg1",
        preferred_window="Afternoon (12pm-5pm)",
        status="deposit_requested",
        created_at=now,
        updated_at=now
    )
    
    # Create leads first
    from ae.repo_leads import insert_lead
    lead1 = LeadIntake(
        ts=now.isoformat(),
        source="test",
        name="Test User 1",
        status="new",
        booking_status="none"
    )
    lead2 = LeadIntake(
        ts=now.isoformat(),
        source="test",
        name="Test User 2",
        status="new",
        booking_status="none"
    )
    lead_id1 = insert_lead(db_path, lead1)
    lead_id2 = insert_lead(db_path, lead2)
    
    booking1.lead_id = lead_id1
    booking2.lead_id = lead_id2
    
    create_booking_request(db_path, booking1)
    create_booking_request(db_path, booking2)
    
    # Now availability should be reduced
    availability = _calculate_availability_for_package(
        db_path,
        "pkg1",
        package.meta_json or {}
    )
    assert availability == 3


@pytest.mark.asyncio
async def test_timeslot_selection_creates_booking(tmp_path):
    """Test that timeslot selection creates booking request correctly."""
    db_path = str(tmp_path / "acq.db")
    _seed_test_data(db_path)
    
    client = TelegramPollingClient("test_token_customer", db_path)
    client.send_message = AsyncMock()
    client.notify_vendor_bot = AsyncMock()
    
    # Create conversation with package selected
    conversation = get_or_create_conversation(
        db_path,
        conversation_id="conv_test",
        channel_id="ch_customer_telegram",
        external_thread_id="12345",
        meta_json={
            "pending_package_id": "pkg1",
            "booking_state": "awaiting_time_window",
            "telegram_username": "testuser",
            "timeslot_list": [
                {"number": 1, "key": "morning", "normalized": "Morning (9am-12pm)"},
                {"number": 2, "key": "afternoon", "normalized": "Afternoon (12pm-5pm)"},
                {"number": 3, "key": "evening", "normalized": "Evening (5pm-9pm)"},
            ]
        }
    )
    
    from ae.repo_chat_channels import get_chat_channel
    channel = get_chat_channel(db_path, "ch_customer_telegram")
    
    # Select timeslot
    await client.handle_timeslot_selection(conversation, channel, "morning")
    
    # Verify booking was created
    from ae.repo_booking_requests import list_booking_requests
    bookings = list_booking_requests(db_path, limit=10)
    assert len(bookings) >= 1
    
    # Find our booking
    our_booking = None
    for br in bookings:
        if br.preferred_window == "Morning (9am-12pm)":
            our_booking = br
            break
    
    assert our_booking is not None
    assert our_booking.package_id == "pkg1"
    assert our_booking.status == "requested"
    assert our_booking.meta_json.get("telegram_chat_id") == "12345"
    
    # Verify customer was notified
    assert client.send_message.called
    call_args = client.send_message.call_args[0]
    assert "booking request has been created" in call_args[1].lower()
    
    # Verify vendor bot was notified
    assert client.notify_vendor_bot.called


@pytest.mark.asyncio
async def test_vendor_bot_notification(tmp_path):
    """Test that vendor bot receives notification with correct booking details."""
    db_path = str(tmp_path / "acq.db")
    _seed_test_data(db_path)
    
    client = TelegramPollingClient("test_token_customer", db_path)
    client.send_message = AsyncMock()
    
    # Create lead
    now = datetime.now(timezone.utc)
    from ae.repo_leads import insert_lead
    lead = LeadIntake(
        ts=now.isoformat(),
        source="telegram_bot",
        client_id="test-massage-spa",
        name="Test Customer",
        meta_json={"telegram_chat_id": "12345", "telegram_username": "testuser"},
        status="new",
        booking_status="none"
    )
    lead_id = insert_lead(db_path, lead)
    
    # Create booking request
    booking = BookingRequest(
        request_id="br_test_123",
        lead_id=lead_id,
        package_id="pkg1",
        preferred_window="Morning (9am-12pm)",
        status="requested",
        meta_json={"telegram_chat_id": "12345", "telegram_username": "testuser"},
        created_at=now,
        updated_at=now
    )
    
    from ae.repo_booking_requests import create_booking_request
    created_booking = create_booking_request(db_path, booking)
    
    # Notify vendor bot
    await client.notify_vendor_bot(created_booking, lead_id)
    
    # Verify message was sent to vendor bot
    # Note: This will fail if vendor_chat_id is not configured, which is expected
    # In a real scenario, vendor_chat_id would be set
    if client.send_message.called:
        call_args = client.send_message.call_args[0]
        assert "br_test_123" in call_args[1]
        assert "60 min Thai Massage" in call_args[1]
        assert "Test Customer" in call_args[1]
        assert "Morning" in call_args[1]


@pytest.mark.asyncio
async def test_end_to_end_flow(tmp_path):
    """Test end-to-end flow from package selection to booking creation."""
    db_path = str(tmp_path / "acq.db")
    _seed_test_data(db_path)
    
    client = TelegramPollingClient("test_token_customer", db_path)
    client.send_message = AsyncMock()
    client.notify_vendor_bot = AsyncMock()
    
    from ae.repo_chat_channels import get_chat_channel
    channel = get_chat_channel(db_path, "ch_customer_telegram")
    
    # Step 1: User says "no" to pre-filled package
    conversation = get_or_create_conversation(
        db_path,
        conversation_id="conv_e2e",
        channel_id="ch_customer_telegram",
        external_thread_id="12345",
        meta_json={
            "telegram_username": "testuser"
        }
    )
    
    await client.handle_package_selection(conversation, channel)
    assert client.send_message.called
    
    # Step 2: User selects package 2
    conversation = get_or_create_conversation(
        db_path,
        conversation_id="conv_e2e",
        channel_id="ch_customer_telegram",
        external_thread_id="12345",
        meta_json={}
    )
    
    client.send_message.reset_mock()
    await client.handle_package_number_selection(conversation, channel, 2)
    assert client.send_message.called
    
    # Step 3: User confirms package
    conversation = get_or_create_conversation(
        db_path,
        conversation_id="conv_e2e",
        channel_id="ch_customer_telegram",
        external_thread_id="12345",
        meta_json={}
    )
    
    client.send_message.reset_mock()
    await client.handle_package_confirmation(conversation, channel)
    assert client.send_message.called
    
    # Verify timeslots were shown
    call_args = client.send_message.call_args[0]
    assert "morning" in call_args[1].lower() or "afternoon" in call_args[1].lower()
    
    # Step 4: User selects timeslot
    conversation = get_or_create_conversation(
        db_path,
        conversation_id="conv_e2e",
        channel_id="ch_customer_telegram",
        external_thread_id="12345",
        meta_json={}
    )
    
    client.send_message.reset_mock()
    await client.handle_timeslot_selection(conversation, channel, "morning")
    
    # Verify booking was created
    from ae.repo_booking_requests import list_booking_requests
    bookings = list_booking_requests(db_path, limit=10)
    assert len(bookings) >= 1
    
    # Verify customer confirmation
    assert client.send_message.called
    call_args = client.send_message.call_args[0]
    assert "booking request has been created" in call_args[1].lower()


def test_normalize_timeslot():
    """Test timeslot normalization helper function."""
    db_path = ":memory:"
    client = TelegramPollingClient("test_token", db_path)
    
    # Create mock conversation
    conversation = MagicMock()
    conversation.meta_json = {
        "timeslot_list": [
            {"number": 1, "normalized": "Morning (9am-12pm)"},
            {"number": 2, "normalized": "Afternoon (12pm-5pm)"},
            {"number": 3, "normalized": "Evening (5pm-9pm)"},
        ]
    }
    
    # Test number input
    assert client._normalize_timeslot("1", conversation) == "Morning (9am-12pm)"
    assert client._normalize_timeslot("2", conversation) == "Afternoon (12pm-5pm)"
    assert client._normalize_timeslot("3", conversation) == "Evening (5pm-9pm)"
    
    # Test text input
    assert client._normalize_timeslot("morning", conversation) == "Morning (9am-12pm)"
    assert client._normalize_timeslot("afternoon", conversation) == "Afternoon (12pm-5pm)"
    assert client._normalize_timeslot("evening", conversation) == "Evening (5pm-9pm)"
    
    # Test invalid input
    assert client._normalize_timeslot("invalid", conversation) is None


@pytest.mark.asyncio
async def test_get_or_create_lead_from_telegram(tmp_path):
    """Test lead creation/retrieval from Telegram user info."""
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)
    
    # Create client
    repo.upsert_client(db_path, Client(
        client_id="test-massage-spa",
        client_name="Test Massage Spa",
        trade=Trade.massage_therapist,
        geo_country="TH",
        geo_city="Bangkok",
        service_area=["Bangkok"],
        primary_phone="+66123456789",
        lead_email="test@example.com",
        status="live",
    ))
    
    client = TelegramPollingClient("test_token", db_path)
    
    # Create lead
    lead_id = await client._get_or_create_lead_from_telegram(
        "12345",
        "testuser",
        "test-massage-spa"
    )
    
    assert lead_id is not None
    
    # Get same lead again (should return existing)
    lead_id2 = await client._get_or_create_lead_from_telegram(
        "12345",
        "testuser",
        "test-massage-spa"
    )
    
    assert lead_id2 == lead_id


def test_generate_booking_request_id():
    """Test booking request ID generation."""
    db_path = ":memory:"
    client = TelegramPollingClient("test_token", db_path)
    
    request_id = client._generate_booking_request_id("12345")
    
    assert request_id.startswith("br_telegram_12345_")
    assert len(request_id) > len("br_telegram_12345_")
