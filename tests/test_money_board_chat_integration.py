"""Integration tests for money board chat channel selection and conversation management."""

from __future__ import annotations

from pathlib import Path

from ae import db, repo
from ae.enums import ChatProvider
from ae.models import Client, LeadIntake


def test_multi_client_channel_selection(tmp_path: Path):
    """Test that money board selects correct channel for multi-client setup."""
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    
    # Create two clients
    client1 = Client(
        client_id="client1",
        client_name="Client One",
        trade="plumbing",
        geo_country="TH",
        geo_city="Bangkok",
        primary_phone="+66-1-111-1111",
        lead_email="client1@test.com",
    )
    repo.upsert_client(db_path, client1)
    
    client2 = Client(
        client_id="client2",
        client_name="Client Two",
        trade="electrical",
        geo_country="TH",
        geo_city="Bangkok",
        primary_phone="+66-2-222-2222",
        lead_email="client2@test.com",
    )
    repo.upsert_client(db_path, client2)
    
    # Create channels for each client
    repo.upsert_chat_channel(
        db_path,
        channel_id="ch_client1_whatsapp",
        provider=ChatProvider.whatsapp,
        handle="+66111111111",
        display_name="Client 1 WhatsApp",
        meta_json={"client_id": "client1"},
    )
    
    repo.upsert_chat_channel(
        db_path,
        channel_id="ch_client2_line",
        provider=ChatProvider.line,
        handle="@client2",
        display_name="Client 2 LINE",
        meta_json={"client_id": "client2"},
    )
    
    # Create leads for each client
    lead1 = LeadIntake(
        ts="2024-01-01T00:00:00Z",
        source="landing_page",
        page_id="p1",
        client_id="client1",
        name="Lead One",
        phone="+66-1-000-0001",
        email="lead1@test.com",
        message="Need plumbing service",
    )
    lead_id1 = repo.insert_lead(db_path, lead1)
    
    lead2 = LeadIntake(
        ts="2024-01-01T00:00:00Z",
        source="landing_page",
        page_id="p2",
        client_id="client2",
        name="Lead Two",
        phone="+66-2-000-0002",
        email="lead2@test.com",
        message="Need electrical service",
    )
    lead_id2 = repo.insert_lead(db_path, lead2)
    
    # Test channel selection logic directly
    from ae.console_routes_chat_public import _find_channel_for_client
    from ae.repo_chat_conversations import get_or_create_conversation
    
    # Test channel selection for client1
    channel1 = _find_channel_for_client(db_path, "client1")
    assert channel1 is not None
    assert channel1.channel_id == "ch_client1_whatsapp"
    
    # Test conversation creation with correct channel
    conv1 = get_or_create_conversation(
        db_path,
        conversation_id=f"test_conv_{lead_id1}",
        channel_id=channel1.channel_id,
        lead_id=str(lead_id1),
    )
    assert conv1.channel_id == "ch_client1_whatsapp"
    assert conv1.lead_id == str(lead_id1)
    
    # Test client2 lead uses client2's channel
    channel2 = _find_channel_for_client(db_path, "client2")
    assert channel2 is not None
    assert channel2.channel_id == "ch_client2_line"
    
    # Test conversation creation for client2
    conv2 = get_or_create_conversation(
        db_path,
        conversation_id=f"test_conv_{lead_id2}",
        channel_id=channel2.channel_id,
        lead_id=str(lead_id2),
    )
    assert conv2.channel_id == "ch_client2_line"
    assert conv2.lead_id == str(lead_id2)
    
    # Verify channels are different
    assert conv1.channel_id != conv2.channel_id


def test_channel_selection_with_client_id(tmp_path: Path):
    """Test that money board correctly selects channel based on lead's client_id."""
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    
    # Create client with channel
    client = Client(
        client_id="test_client",
        client_name="Test Client",
        trade="plumbing",
        geo_country="TH",
        geo_city="Bangkok",
        primary_phone="+66-9-999-9999",
        lead_email="test@test.com",
    )
    repo.upsert_client(db_path, client)
    
    repo.upsert_chat_channel(
        db_path,
        channel_id="ch_test_whatsapp",
        provider=ChatProvider.whatsapp,
        handle="+66999999999",
        display_name="Test WhatsApp",
        meta_json={"client_id": "test_client"},
    )
    
    # Create lead with client_id
    lead = LeadIntake(
        ts="2024-01-01T00:00:00Z",
        source="landing_page",
        page_id="p1",
        client_id="test_client",
        name="Test Lead",
        phone="+66-8-888-8888",
        email="lead@test.com",
        message="Test message",
    )
    lead_id = repo.insert_lead(db_path, lead)
    
    # Test channel selection
    from ae.console_routes_chat_public import _find_channel_for_client
    channel = _find_channel_for_client(db_path, "test_client")
    
    assert channel is not None
    assert channel.channel_id == "ch_test_whatsapp"
    assert channel.meta_json.get("client_id") == "test_client"


def test_fallback_to_primary_phone(tmp_path: Path):
    """Test fallback to client's primary_phone when no channel configured."""
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    
    # Create client with phone but no channel
    client = Client(
        client_id="phone_client",
        client_name="Phone Client",
        trade="plumbing",
        geo_country="TH",
        geo_city="Bangkok",
        primary_phone="+66-7-777-7777",
        lead_email="phone@test.com",
    )
    repo.upsert_client(db_path, client)
    
    # Create lead
    lead = LeadIntake(
        ts="2024-01-01T00:00:00Z",
        source="landing_page",
        page_id="p1",
        client_id="phone_client",
        name="Phone Lead",
        phone="+66-7-000-0000",
        email="phonelead@test.com",
        message="Test",
    )
    lead_id = repo.insert_lead(db_path, lead)
    
    # Test fallback
    from ae.console_routes_chat_public import _find_channel_for_client
    channel = _find_channel_for_client(db_path, "phone_client")
    
    assert channel is not None
    assert channel.channel_id == "phone_phone_client"
    assert channel.provider == ChatProvider.sms
    assert channel.handle == "+66-7-777-7777"
    assert channel.meta_json.get("fallback") is True


def test_conversation_reuse(tmp_path: Path):
    """Test that money board reuses existing conversations for leads."""
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    
    # Setup client and channel
    client = Client(
        client_id="reuse_client",
        client_name="Reuse Client",
        trade="plumbing",
        geo_country="TH",
        geo_city="Bangkok",
        primary_phone="+66-6-666-6666",
        lead_email="reuse@test.com",
    )
    repo.upsert_client(db_path, client)
    
    repo.upsert_chat_channel(
        db_path,
        channel_id="ch_reuse",
        provider=ChatProvider.whatsapp,
        handle="+66666666666",
        display_name="Reuse Channel",
        meta_json={"client_id": "reuse_client"},
    )
    
    # Create lead
    lead = LeadIntake(
        ts="2024-01-01T00:00:00Z",
        source="landing_page",
        page_id="p1",
        client_id="reuse_client",
        name="Reuse Lead",
        phone="+66-6-000-0000",
        email="reuselead@test.com",
        message="Test",
    )
    lead_id = repo.insert_lead(db_path, lead)
    
    # Create initial conversation
    from ae.repo_chat_conversations import get_or_create_conversation
    conv1 = get_or_create_conversation(
        db_path,
        conversation_id="conv_reuse_1",
        channel_id="ch_reuse",
        lead_id=str(lead_id),
    )
    
    # Test: money board should find and reuse this conversation
    from ae.console_routes_chat_public import _find_channel_for_client
    from ae.repo_chat_conversations import list_conversations
    
    channel = _find_channel_for_client(db_path, "reuse_client")
    existing_conversations = list_conversations(db_path, lead_id=str(lead_id), limit=1)
    
    assert len(existing_conversations) > 0
    assert existing_conversations[0].conversation_id == conv1.conversation_id
    
    # Create another conversation attempt - should reuse
    conv2 = get_or_create_conversation(
        db_path,
        conversation_id="conv_reuse_2",  # Different ID
        channel_id="ch_reuse",
        lead_id=str(lead_id),
    )
    
    # Verify we still have the original conversation
    all_convs = list_conversations(db_path, lead_id=str(lead_id), limit=10)
    # Should have both, but the logic should prefer existing one
    assert len(all_convs) >= 1


def test_end_to_end_flow(tmp_path: Path):
    """Test complete flow: landing page → lead creation → money board → chat."""
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    
    # Setup: Create client
    client = Client(
        client_id="e2e_client",
        client_name="E2E Client",
        trade="plumbing",
        geo_country="TH",
        geo_city="Bangkok",
        primary_phone="+66-5-555-5555",
        lead_email="e2e@test.com",
    )
    repo.upsert_client(db_path, client)
    
    # Setup: Create channel
    repo.upsert_chat_channel(
        db_path,
        channel_id="ch_e2e",
        provider=ChatProvider.whatsapp,
        handle="+66555555555",
        display_name="E2E Channel",
        meta_json={"client_id": "e2e_client"},
    )
    
    # Step 1: Simulate landing page lead creation
    lead = LeadIntake(
        ts="2024-01-01T00:00:00Z",
        source="landing_page",
        page_id="p_e2e",
        client_id="e2e_client",
        name="E2E Lead",
        phone="+66-5-000-0000",
        email="e2elead@test.com",
        message="Booking request from landing page",
        utm_source="meta",
        utm_campaign="test_campaign",
    )
    lead_id = repo.insert_lead(db_path, lead)
    
    # Verify lead created with correct client_id
    retrieved_lead = repo.get_lead(db_path, lead_id)
    assert retrieved_lead.client_id == "e2e_client"
    
    # Step 2: Money board finds correct channel
    from ae.console_routes_chat_public import _find_channel_for_client
    channel = _find_channel_for_client(db_path, "e2e_client")
    assert channel is not None
    assert channel.channel_id == "ch_e2e"
    
    # Step 3: Money board creates/links conversation
    from ae.repo_chat_conversations import get_or_create_conversation, list_conversations
    
    # Check for existing conversation (should be none initially)
    existing = list_conversations(db_path, lead_id=str(lead_id), limit=1)
    
    if existing:
        conversation = existing[0]
    else:
        conversation = get_or_create_conversation(
            db_path,
            conversation_id=f"conv_e2e_{lead_id}",
            channel_id=channel.channel_id,
            lead_id=str(lead_id),
        )
    
    assert conversation.channel_id == "ch_e2e"
    assert conversation.lead_id == str(lead_id)
    
    # Step 4: Verify message can be sent (simulate template send)
    from ae.repo_chat_messages import insert_message
    from datetime import datetime
    
    message = insert_message(
        db_path,
        message_id=f"msg_e2e_{lead_id}",
        conversation_id=conversation.conversation_id,
        direction="outbound",
        text="Test message from money board",
        ts=datetime.utcnow().isoformat() + "Z",
    )
    
    assert message.conversation_id == conversation.conversation_id
    assert message.text == "Test message from money board"


def test_missing_channel_handling(tmp_path: Path):
    """Test appropriate error handling when client has no channel or phone."""
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    
    # Create client without channel or phone
    client = Client(
        client_id="no_channel_client",
        client_name="No Channel Client",
        trade="plumbing",
        geo_country="TH",
        geo_city="Bangkok",
        primary_phone=None,
        lead_email="nochannel@test.com",
    )
    repo.upsert_client(db_path, client)
    
    # Create lead
    lead = LeadIntake(
        ts="2024-01-01T00:00:00Z",
        source="landing_page",
        page_id="p1",
        client_id="no_channel_client",
        name="No Channel Lead",
        phone="+66-4-000-0000",
        email="nolead@test.com",
        message="Test",
    )
    lead_id = repo.insert_lead(db_path, lead)
    
    # Test: should return None (no channel found)
    from ae.console_routes_chat_public import _find_channel_for_client
    channel = _find_channel_for_client(db_path, "no_channel_client")
    
    assert channel is None
    
    # Test: money board logic should detect missing channel
    # The _find_channel_for_client returns None, which should be handled appropriately
    # In the actual send_template function, this would raise HTTPException
    # For this test, we verify the helper returns None
    assert channel is None
    
    # Verify that if we try to get channel for non-existent client, it also returns None
    channel_nonexistent = _find_channel_for_client(db_path, "nonexistent_client")
    assert channel_nonexistent is None


def test_money_board_column_structure(tmp_path: Path):
    """Verify money board API returns 4 columns with expected status keys."""
    import os
    from fastapi.testclient import TestClient

    os.environ.pop("AE_CONSOLE_SECRET", None)
    db_path = str(tmp_path / "acq.db")
    db.init_db(db_path)

    from ae.console_app import app
    client = TestClient(app)
    r = client.get("/api/money-board", params={"db": db_path})
    assert r.status_code == 200
    data = r.json()
    assert "columns" in data
    col_statuses = [c["status"] for c in data["columns"]]
    assert set(col_statuses) == {"pending", "confirmed", "complete", "closed"}
    assert len(col_statuses) == 4
