from ae import db, repo
from ae.enums import ChatProvider


def test_chat_channel_upsert_get_list(tmp_path):
    db_path = str(tmp_path / "ae.db")
    db.init_db(db_path)

    ch1 = repo.upsert_chat_channel(
        db_path,
        channel_id="ch_line_1",
        provider=ChatProvider.line,
        handle="U123",
        display_name="Alice",
        meta_json={"lang": "en"},
    )
    assert ch1.channel_id == "ch_line_1"
    assert ch1.provider == ChatProvider.line
    assert ch1.handle == "U123"

    # upsert (update)
    ch1b = repo.upsert_chat_channel(
        db_path,
        channel_id="ch_line_1",
        provider=ChatProvider.line,
        handle="U123",
        display_name="Alice v2",
        meta_json={"lang": "th"},
    )
    assert ch1b.display_name == "Alice v2"
    assert ch1b.meta_json.get("lang") == "th"

    got = repo.get_chat_channel(db_path, "ch_line_1")
    assert got is not None
    assert got.display_name == "Alice v2"

    repo.upsert_chat_channel(
        db_path,
        channel_id="ch_wa_1",
        provider=ChatProvider.whatsapp,
        handle="+66000000000",
        display_name="Bob",
        meta_json={},
    )

    all_items = repo.list_chat_channels(db_path)
    assert len(all_items) == 2

    wa_items = repo.list_chat_channels(db_path, provider=ChatProvider.whatsapp)
    assert len(wa_items) == 1
    assert wa_items[0].channel_id == "ch_wa_1"


def test_find_channel_for_client_with_client_id(tmp_path):
    """Test _find_channel_for_client helper filters by client_id correctly."""
    from ae.console_routes_chat_public import _find_channel_for_client
    from ae.models import Client
    
    db_path = str(tmp_path / "ae.db")
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
    
    # Test: find channel for client1 should return client1's channel
    channel1 = _find_channel_for_client(db_path, "client1")
    assert channel1 is not None
    assert channel1.channel_id == "ch_client1_whatsapp"
    assert channel1.provider == ChatProvider.whatsapp
    
    # Test: find channel for client2 should return client2's channel
    channel2 = _find_channel_for_client(db_path, "client2")
    assert channel2 is not None
    assert channel2.channel_id == "ch_client2_line"
    assert channel2.provider == ChatProvider.line
    
    # Test: find channel with provider filter
    channel1_wa = _find_channel_for_client(db_path, "client1", ChatProvider.whatsapp)
    assert channel1_wa is not None
    assert channel1_wa.channel_id == "ch_client1_whatsapp"
    
    channel1_line = _find_channel_for_client(db_path, "client1", ChatProvider.line)
    assert channel1_line is None  # client1 doesn't have LINE channel
    
    # Test: fallback to primary_phone when no channel
    client3 = Client(
        client_id="client3",
        client_name="Client Three",
        trade="hvac",
        geo_country="TH",
        geo_city="Bangkok",
        primary_phone="+66-3-333-3333",
        lead_email="client3@test.com",
    )
    repo.upsert_client(db_path, client3)
    
    channel3 = _find_channel_for_client(db_path, "client3")
    assert channel3 is not None
    assert channel3.channel_id == "phone_client3"
    assert channel3.provider == ChatProvider.sms
    assert channel3.handle == "+66-3-333-3333"
    assert channel3.meta_json.get("fallback") is True
    
    # Test: no channel and no phone returns None
    client4 = Client(
        client_id="client4",
        client_name="Client Four",
        trade="carpentry",
        geo_country="TH",
        geo_city="Bangkok",
        primary_phone=None,
        lead_email="client4@test.com",
    )
    repo.upsert_client(db_path, client4)
    
    channel4 = _find_channel_for_client(db_path, "client4")
    assert channel4 is None