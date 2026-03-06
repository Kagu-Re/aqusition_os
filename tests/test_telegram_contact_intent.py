"""Tests for Telegram bot Contact Us flow: intent_contact, keyword responses, conversation mode."""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone

from ae import db as dbmod, repo
from ae.models import Client, ServicePackage, ChatChannel
from ae.enums import Trade, ChatProvider
from ae.telegram_polling import TelegramPollingClient
from ae.repo_chat_channels import upsert_chat_channel, get_chat_channel
from ae.repo_chat_conversations import get_or_create_conversation, get_conversation


def _seed_test_data(db_path: str, hours: str = "9am-6pm"):
    """Seed database with test data for contact intent tests."""
    dbmod.init_db(db_path)

    repo.upsert_client(db_path, Client(
        client_id="test-massage-spa",
        client_name="Test Massage Spa",
        trade=Trade.massage,
        geo_country="TH",
        geo_city="Bangkok",
        service_area=["Bangkok"],
        primary_phone="+66123456789",
        lead_email="test@example.com",
        status="live",
        hours=hours,
    ))

    now = datetime.now(timezone.utc)
    for pkg in [
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
    ]:
        repo.create_package(db_path, pkg)

    upsert_chat_channel(
        db_path,
        channel_id="ch_customer_telegram",
        provider=ChatProvider.telegram,
        handle="@test_bot",
        meta_json={
            "telegram_bot_token": "test_token_customer",
            "client_id": "test-massage-spa",
            "bot_type": "customer",
        },
    )


@pytest.mark.asyncio
async def test_handle_contact_intent_sends_welcome(tmp_path):
    """handle_contact_intent sends welcome with options and stores conversation_mode."""
    db_path = str(tmp_path / "acq.db")
    _seed_test_data(db_path)

    client = TelegramPollingClient("test_token_customer", db_path)
    client.send_message = AsyncMock()

    channel = get_chat_channel(db_path, "ch_customer_telegram")
    conversation = get_or_create_conversation(
        db_path,
        conversation_id="conv_contact_test",
        channel_id="ch_customer_telegram",
        external_thread_id="12345",
        meta_json={},
    )

    await client.handle_contact_intent(conversation, channel)

    assert client.send_message.called
    call_args = client.send_message.call_args[0]
    msg = call_args[1]
    assert "contact" in msg.lower() or "help" in msg.lower() or "reach" in msg.lower()
    assert "1" in msg or "2" in msg or "3" in msg
    assert "packages" in msg.lower()
    assert "question" in msg.lower()

    conv_after = get_conversation(db_path, "conv_contact_test")
    assert conv_after is not None
    assert conv_after.meta_json.get("conversation_mode") == "contact"


@pytest.mark.asyncio
async def test_contact_intent_stores_conversation_mode(tmp_path):
    """After handle_contact_intent, conversation meta has conversation_mode=contact."""
    db_path = str(tmp_path / "acq.db")
    _seed_test_data(db_path)

    client = TelegramPollingClient("test_token_customer", db_path)
    client.send_message = AsyncMock()

    channel = get_chat_channel(db_path, "ch_customer_telegram")
    conversation = get_or_create_conversation(
        db_path,
        conversation_id="conv_mode_test",
        channel_id="ch_customer_telegram",
        external_thread_id="12345",
        meta_json={},
    )

    await client.handle_contact_intent(conversation, channel)

    conversation = get_conversation(db_path, "conv_mode_test")
    assert conversation is not None
    assert conversation.meta_json.get("conversation_mode") == "contact"


@pytest.mark.asyncio
async def test_keyword_hours_returns_client_hours(tmp_path):
    """In contact mode, 'hours' returns client hours."""
    db_path = str(tmp_path / "acq.db")
    _seed_test_data(db_path, hours="10am-8pm")

    client = TelegramPollingClient("test_token_customer", db_path)
    client.send_message = AsyncMock()

    channel = get_chat_channel(db_path, "ch_customer_telegram")
    conversation = get_or_create_conversation(
        db_path,
        conversation_id="conv_hours_test",
        channel_id="ch_customer_telegram",
        external_thread_id="12345",
        meta_json={"conversation_mode": "contact"},
    )

    await client._handle_contact_mode_message(conversation, channel, "hours")

    assert client.send_message.called
    msg = client.send_message.call_args[0][1]
    assert "10am-8pm" in msg or "open" in msg.lower()


@pytest.mark.asyncio
async def test_keyword_location_returns_service_area(tmp_path):
    """In contact mode, 'location' returns service area."""
    db_path = str(tmp_path / "acq.db")
    _seed_test_data(db_path)

    client = TelegramPollingClient("test_token_customer", db_path)
    client.send_message = AsyncMock()

    channel = get_chat_channel(db_path, "ch_customer_telegram")
    conversation = get_or_create_conversation(
        db_path,
        conversation_id="conv_loc_test",
        channel_id="ch_customer_telegram",
        external_thread_id="12345",
        meta_json={"conversation_mode": "contact"},
    )

    await client._handle_contact_mode_message(conversation, channel, "location")

    assert client.send_message.called
    msg = client.send_message.call_args[0][1]
    assert "Bangkok" in msg or "serve" in msg.lower()


@pytest.mark.asyncio
async def test_keyword_packages_triggers_package_list(tmp_path):
    """In contact mode, 'packages' triggers handle_package_selection."""
    db_path = str(tmp_path / "acq.db")
    _seed_test_data(db_path)

    client = TelegramPollingClient("test_token_customer", db_path)
    client.send_message = AsyncMock()

    channel = get_chat_channel(db_path, "ch_customer_telegram")
    conversation = get_or_create_conversation(
        db_path,
        conversation_id="conv_pkg_test",
        channel_id="ch_customer_telegram",
        external_thread_id="12345",
        meta_json={"conversation_mode": "contact"},
    )

    await client._handle_contact_mode_message(conversation, channel, "packages")

    assert client.send_message.called
    msg = client.send_message.call_args[0][1]
    assert "60 min" in msg or "Thai Massage" in msg or "package" in msg.lower()


@pytest.mark.asyncio
async def test_contact_mode_unmatched_text_fallback(tmp_path):
    """In contact mode, unmatched text gets fallback about sharing with team."""
    db_path = str(tmp_path / "acq.db")
    _seed_test_data(db_path)

    client = TelegramPollingClient("test_token_customer", db_path)
    client.send_message = AsyncMock()

    channel = get_chat_channel(db_path, "ch_customer_telegram")
    conversation = get_or_create_conversation(
        db_path,
        conversation_id="conv_fallback_test",
        channel_id="ch_customer_telegram",
        external_thread_id="12345",
        meta_json={"conversation_mode": "contact"},
    )

    await client._handle_contact_mode_message(conversation, channel, "random question about something")

    assert client.send_message.called
    msg = client.send_message.call_args[0][1]
    assert "share" in msg.lower() or "team" in msg.lower() or "message" in msg.lower()
    assert "packages" in msg.lower() or "hours" in msg.lower()
