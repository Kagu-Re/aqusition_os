"""Integration tests for Contact Us chat journey: deep link, welcome flow, contact-to-packages."""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone

from ae import db as dbmod, repo
from ae.models import Client, ServicePackage
from ae.enums import Trade, ChatProvider
from ae.telegram_polling import TelegramPollingClient
from ae.repo_chat_channels import upsert_chat_channel, get_chat_channel
from ae.repo_chat_conversations import get_or_create_conversation, get_conversation


def _seed_test_data(db_path: str):
    """Seed database for Contact Us journey tests."""
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
        hours="9am-6pm",
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
async def test_start_intent_contact_flow_e2e(tmp_path):
    """Simulate /start intent_contact via handle_message; verify contact-specific response."""
    db_path = str(tmp_path / "acq.db")
    _seed_test_data(db_path)

    client = TelegramPollingClient("test_token_customer", db_path)
    client.send_message = AsyncMock()

    message = {
        "chat": {"id": 99999},
        "text": "/start intent_contact",
        "message_id": 1001,
        "update_id": 5001,
        "from": {"id": 99999, "username": "testuser"},
    }

    await client.handle_message(message)

    assert client.send_message.called
    msg = client.send_message.call_args[0][1]
    assert "contact" in msg.lower() or "reach" in msg.lower() or "help" in msg.lower()
    assert "1" in msg or "2" in msg or "3" in msg
    assert "packages" in msg.lower()

    conv = get_conversation(db_path, "conv_telegram_99999")
    assert conv is not None
    assert conv.meta_json.get("conversation_mode") == "contact"


@pytest.mark.asyncio
async def test_contact_yes_confirmation_proceeds_to_booking(tmp_path):
    """Contact flow: select package, say 'yes' -> should enter timeslot flow, not fallback message."""
    db_path = str(tmp_path / "acq.db")
    _seed_test_data(db_path)

    client = TelegramPollingClient("test_token_customer", db_path)
    client.send_message = AsyncMock()

    channel = get_chat_channel(db_path, "ch_customer_telegram")
    get_or_create_conversation(
        db_path,
        conversation_id="conv_telegram_77777",
        channel_id="ch_customer_telegram",
        external_thread_id="77777",
        meta_json={
            "conversation_mode": "contact",
            "pending_package_id": "pkg1",
            "package_list": [
                {"number": 1, "package_id": "pkg1", "name": "60 min Thai Massage"},
                {"number": 2, "package_id": "pkg2", "name": "90 min Aromatherapy"},
            ],
        },
    )

    await client.handle_message({
        "chat": {"id": 77777},
        "text": "yes",
        "message_id": 2001,
        "from": {"id": 77777},
    })

    assert client.send_message.called
    msg = client.send_message.call_args[0][1]
    assert "morning" in msg.lower() or "afternoon" in msg.lower() or "evening" in msg.lower()
    assert "when would you" in msg.lower() or "time window" in msg.lower() or "prefer" in msg.lower()
    assert "share your message with our team" not in msg.lower()


@pytest.mark.asyncio
async def test_contact_to_packages_flow(tmp_path):
    """Contact mode: send 'packages' -> verify package list in response."""
    db_path = str(tmp_path / "acq.db")
    _seed_test_data(db_path)

    client = TelegramPollingClient("test_token_customer", db_path)
    client.send_message = AsyncMock()

    channel = get_chat_channel(db_path, "ch_customer_telegram")
    conversation = get_or_create_conversation(
        db_path,
        conversation_id="conv_contact_pkg",
        channel_id="ch_customer_telegram",
        external_thread_id="88888",
        meta_json={"conversation_mode": "contact"},
    )

    await client._handle_contact_mode_message(conversation, channel, "packages")

    assert client.send_message.called
    msg = client.send_message.call_args[0][1]
    assert "60 min" in msg or "Thai Massage" in msg
    assert "90 min" in msg or "Aromatherapy" in msg
    assert "800" in msg or "1200" in msg
    assert "1" in msg and "2" in msg
