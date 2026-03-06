
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ae.db import init_db
from ae.repo_chat_channels import upsert_chat_channel
from ae.repo_chat_conversations import get_or_create_conversation
from ae.chat_automation import install_chat_automation_hooks, run_due_chat_automations
from ae.event_bus import EventBus
from ae.enums import ChatProvider


def test_chat_automation_payment_request(tmp_path: Path):
    db_path = str(tmp_path / "t.db")
    init_db(db_path)

    install_chat_automation_hooks()

    upsert_chat_channel(
        db_path,
        channel_id="ch1",
        provider=ChatProvider.other,
        handle="u1",
        display_name="U1",
        meta_json={},
    )
    get_or_create_conversation(
        db_path,
        conversation_id="conv1",
        channel_id="ch1",
        lead_id="L1",
        booking_id="lead-L1",
    )

    # inbound asks about price -> schedule payment_request
    EventBus.emit_topic(
        db_path,
        topic="op.chat.message_received",
        aggregate_type="chat",
        aggregate_id="conv1",
        payload={"conversation_id": "conv1", "text": "what is the price?"},
    )

    sent = run_due_chat_automations(db_path, now=datetime.utcnow(), limit=10)
    assert sent == 1
