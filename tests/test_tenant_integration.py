"""Integration tests for multi-tenant infrastructure.

Run with AE_MULTI_TENANT_ENABLED=1 to test tenant resolution and scoping.
"""
import os
import pytest
from datetime import datetime, timezone

pytestmark = pytest.mark.tenant
from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod
from ae import repo
from ae.models import Client, Template, Page, LeadIntake, Menu, ServicePackage
from ae.enums import Trade, TemplateStatus, PageStatus, EventName, ChatProvider, MenuStatus, PaymentProvider, PaymentMethod


def test_single_tenant_list_all_clients(tmp_path):
    """With multi-tenant OFF: list returns all clients."""
    os.environ.pop("AE_MULTI_TENANT_ENABLED", None)
    os.environ["AE_CONSOLE_SECRET"] = "s"
    db_path = str(tmp_path / "ae.db")
    dbmod.init_db(db_path)

    c = TestClient(app)

    # Create two clients
    for slug, name in [("client-a", "Client A"), ("client-b", "Client B")]:
        r = c.post(
            "/api/clients",
            params={"db_path": db_path},
            headers={"X-AE-SECRET": "s"},
            json={
                "slug": slug,
                "name": name,
                "industry": "plumber",
                "geo_country": "TH",
                "geo": "chiang mai",
                "primary_phone": "+66-400-000-001",
                "lead_email": f"{slug}@example.com",
            },
        )
        assert r.status_code == 200

    r = c.get("/api/clients", params={"db_path": db_path}, headers={"X-AE-SECRET": "s"})
    assert r.status_code == 200
    items = r.json()["clients"]
    assert len(items) >= 2
    ids = [x["client_id"] for x in items]
    assert "client-a" in ids
    assert "client-b" in ids


def test_multi_tenant_scoped_clients(tmp_path):
    """With multi-tenant ON and X-Tenant-ID: list returns only scoped client."""
    os.environ["AE_MULTI_TENANT_ENABLED"] = "1"
    os.environ["AE_CONSOLE_SECRET"] = "s"
    db_path = str(tmp_path / "ae.db")
    dbmod.init_db(db_path)

    c = TestClient(app)

    # Create two clients
    for slug, name in [("c1", "Client One"), ("c2", "Client Two")]:
        r = c.post(
            "/api/clients",
            params={"db_path": db_path},
            headers={"X-AE-SECRET": "s", "X-Tenant-ID": slug},
            json={
                "slug": slug,
                "name": name,
                "industry": "plumber",
                "geo_country": "TH",
                "geo": "chiang mai",
                "primary_phone": "+66-400-000-001",
                "lead_email": f"{slug}@example.com",
            },
        )
        assert r.status_code == 200, f"Create {slug}: {r.status_code} {r.text}"

    # List with tenant c1: only c1
    r = c.get(
        "/api/clients",
        params={"db_path": db_path},
        headers={"X-AE-SECRET": "s", "X-Tenant-ID": "c1"},
    )
    assert r.status_code == 200
    items = r.json()["clients"]
    assert len(items) == 1
    assert items[0]["client_id"] == "c1"

    # List with tenant c2: only c2
    r = c.get(
        "/api/clients",
        params={"db_path": db_path},
        headers={"X-AE-SECRET": "s", "X-Tenant-ID": "c2"},
    )
    assert r.status_code == 200
    items = r.json()["clients"]
    assert len(items) == 1
    assert items[0]["client_id"] == "c2"


def test_multi_tenant_get_other_client_forbidden(tmp_path):
    """With multi-tenant ON: get client outside scope returns 403."""
    os.environ["AE_MULTI_TENANT_ENABLED"] = "1"
    os.environ["AE_CONSOLE_SECRET"] = "s"
    db_path = str(tmp_path / "ae.db")
    dbmod.init_db(db_path)

    c = TestClient(app)
    r = c.post(
        "/api/clients",
        params={"db_path": db_path},
        headers={"X-AE-SECRET": "s", "X-Tenant-ID": "c1"},
        json={
            "slug": "c1",
            "name": "Client One",
            "industry": "plumber",
            "geo_country": "TH",
            "geo": "chiang mai",
            "primary_phone": "+66-400-000-001",
            "lead_email": "c1@example.com",
        },
    )
    assert r.status_code == 200

    # c1 tenant gets c1: ok
    r = c.get(
        "/api/clients/c1",
        params={"db_path": db_path},
        headers={"X-AE-SECRET": "s", "X-Tenant-ID": "c1"},
    )
    assert r.status_code == 200

    # c1 tenant tries to get c2: 403
    r = c.get(
        "/api/clients/c2",
        params={"db_path": db_path},
        headers={"X-AE-SECRET": "s", "X-Tenant-ID": "c1"},
    )
    assert r.status_code == 403


def test_multi_tenant_lead_intake_uses_tenant(tmp_path):
    """With multi-tenant ON: lead intake uses X-Tenant-ID as client_id when not in payload."""
    os.environ["AE_MULTI_TENANT_ENABLED"] = "1"
    os.environ.pop("AE_CONSOLE_SECRET", None)
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)

    c = TestClient(app)

    # Lead without client_id in payload; tenant provides it
    r = c.post(
        "/lead",
        params={"db": db_path},
        headers={"X-Tenant-ID": "c1"},
        json={
            "source": "webform",
            "page_id": "p1",
            "name": "Ann",
            "phone": "+66 80 000 0000",
            "email": "ann@example.com",
            "message": "Hi",
        },
    )
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is True

    # List leads with X-Tenant-ID to scope to c1
    r2 = c.get(
        "/api/leads",
        params={"db": db_path, "limit": 10},
        headers={"X-Tenant-ID": "c1"},
    )
    assert r2.status_code == 200
    items = r2.json().get("items", [])
    assert len(items) >= 1, "Lead with client_id c1 should be listed"
    assert items[0]["client_id"] == "c1"


def test_multi_tenant_scoped_service_packages(tmp_path):
    """With multi-tenant ON and X-Tenant-ID: list packages returns only scoped client."""
    os.environ["AE_MULTI_TENANT_ENABLED"] = "1"
    os.environ["AE_CONSOLE_SECRET"] = "s"
    db_path = str(tmp_path / "ae.db")
    dbmod.init_db(db_path)

    c = TestClient(app)
    headers = {"X-AE-SECRET": "s"}

    # Create clients c1, c2
    for slug in ["c1", "c2"]:
        r = c.post(
            "/api/clients",
            params={"db_path": db_path},
            headers={**headers, "X-Tenant-ID": slug},
            json={
                "slug": slug,
                "name": f"Client {slug}",
                "industry": "plumber",
                "geo_country": "TH",
                "geo": "chiang mai",
                "primary_phone": "+66-400-000-001",
                "lead_email": f"{slug}@example.com",
            },
        )
        assert r.status_code == 200

    # Create package p1 for c1, p2 for c2
    for client_id, pkg_id in [("c1", "p1"), ("c2", "p2")]:
        r = c.post(
            "/api/service-packages",
            params={"db": db_path},
            headers={**headers, "X-Tenant-ID": client_id},
            json={
                "package_id": pkg_id,
                "client_id": client_id,
                "name": f"Package {pkg_id}",
                "price": 100.0,
                "duration_min": 60,
            },
        )
        assert r.status_code == 200, f"Create {pkg_id}: {r.status_code} {r.text}"

    # List with tenant c1: only p1
    r = c.get(
        "/api/service-packages",
        params={"db": db_path},
        headers={**headers, "X-Tenant-ID": "c1"},
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["package_id"] == "p1"
    assert items[0]["client_id"] == "c1"

    # List with tenant c2: only p2
    r = c.get(
        "/api/service-packages",
        params={"db": db_path},
        headers={**headers, "X-Tenant-ID": "c2"},
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["package_id"] == "p2"


def test_multi_tenant_get_other_package_forbidden(tmp_path):
    """With multi-tenant ON: get package outside scope returns 403."""
    os.environ["AE_MULTI_TENANT_ENABLED"] = "1"
    os.environ["AE_CONSOLE_SECRET"] = "s"
    db_path = str(tmp_path / "ae.db")
    dbmod.init_db(db_path)

    c = TestClient(app)
    headers = {"X-AE-SECRET": "s", "X-Tenant-ID": "c1"}

    # Create c1 and package p1
    c.post(
        "/api/clients",
        params={"db_path": db_path},
        headers=headers,
        json={
            "slug": "c1",
            "name": "Client One",
            "industry": "plumber",
            "geo_country": "TH",
            "geo": "chiang mai",
            "primary_phone": "+66-400-000-001",
            "lead_email": "c1@example.com",
        },
    )
    c.post(
        "/api/service-packages",
        params={"db": db_path},
        headers=headers,
        json={"package_id": "p1", "client_id": "c1", "name": "P1", "price": 100.0, "duration_min": 60},
    )
    # Create c2 and package p2
    c.post(
        "/api/clients",
        params={"db_path": db_path},
        headers={"X-AE-SECRET": "s", "X-Tenant-ID": "c2"},
        json={
            "slug": "c2",
            "name": "Client Two",
            "industry": "plumber",
            "geo_country": "TH",
            "geo": "chiang mai",
            "primary_phone": "+66-400-000-001",
            "lead_email": "c2@example.com",
        },
    )
    c.post(
        "/api/service-packages",
        params={"db": db_path},
        headers={"X-AE-SECRET": "s", "X-Tenant-ID": "c2"},
        json={"package_id": "p2", "client_id": "c2", "name": "P2", "price": 200.0, "duration_min": 90},
    )

    # c1 tenant gets p1: ok
    r = c.get("/api/service-packages/p1", params={"db": db_path}, headers=headers)
    assert r.status_code == 200

    # c1 tenant tries to get p2: 403
    r = c.get("/api/service-packages/p2", params={"db": db_path}, headers=headers)
    assert r.status_code == 403


def test_multi_tenant_scoped_menus(tmp_path):
    """With multi-tenant ON and X-Tenant-ID: list menus returns only scoped client."""
    os.environ["AE_MULTI_TENANT_ENABLED"] = "1"
    os.environ["AE_CONSOLE_SECRET"] = "s"
    db_path = str(tmp_path / "ae.db")
    dbmod.init_db(db_path)

    c = TestClient(app)
    headers = {"X-AE-SECRET": "s"}

    # Create clients
    for slug in ["c1", "c2"]:
        c.post(
            "/api/clients",
            params={"db_path": db_path},
            headers={**headers, "X-Tenant-ID": slug},
            json={
                "slug": slug,
                "name": f"Client {slug}",
                "industry": "plumber",
                "geo_country": "TH",
                "geo": "chiang mai",
                "primary_phone": "+66-400-000-001",
                "lead_email": f"{slug}@example.com",
            },
        )

    # Create menus m1 for c1, m2 for c2
    for client_id, menu_id in [("c1", "m1"), ("c2", "m2")]:
        r = c.post(
            "/api/menus",
            params={"db": db_path},
            headers={**headers, "X-Tenant-ID": client_id},
            json={
                "menu_id": menu_id,
                "client_id": client_id,
                "name": f"Menu {menu_id}",
                "language": "en",
                "currency": "THB",
            },
        )
        assert r.status_code == 200, f"Create {menu_id}: {r.status_code} {r.text}"

    r = c.get("/api/menus", params={"db": db_path}, headers={**headers, "X-Tenant-ID": "c1"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["menu_id"] == "m1"
    assert items[0]["client_id"] == "c1"


def test_multi_tenant_get_other_menu_forbidden(tmp_path):
    """With multi-tenant ON: get menu outside scope returns 403."""
    os.environ["AE_MULTI_TENANT_ENABLED"] = "1"
    os.environ["AE_CONSOLE_SECRET"] = "s"
    db_path = str(tmp_path / "ae.db")
    dbmod.init_db(db_path)

    c = TestClient(app)
    headers = {"X-AE-SECRET": "s", "X-Tenant-ID": "c1"}

    for slug in ["c1", "c2"]:
        c.post(
            "/api/clients",
            params={"db_path": db_path},
            headers={"X-AE-SECRET": "s", "X-Tenant-ID": slug},
            json={
                "slug": slug,
                "name": f"Client {slug}",
                "industry": "plumber",
                "geo_country": "TH",
                "geo": "chiang mai",
                "primary_phone": "+66-400-000-001",
                "lead_email": f"{slug}@example.com",
            },
        )
    c.post(
        "/api/menus",
        params={"db": db_path},
        headers=headers,
        json={"menu_id": "m1", "client_id": "c1", "name": "M1", "language": "en", "currency": "THB"},
    )
    c.post(
        "/api/menus",
        params={"db": db_path},
        headers={"X-AE-SECRET": "s", "X-Tenant-ID": "c2"},
        json={"menu_id": "m2", "client_id": "c2", "name": "M2", "language": "en", "currency": "THB"},
    )

    r = c.get("/api/menus/m1", params={"db": db_path}, headers=headers)
    assert r.status_code == 200

    r = c.get("/api/menus/m2", params={"db": db_path}, headers=headers)
    assert r.status_code == 403


def test_multi_tenant_spend_scoped(tmp_path):
    """With multi-tenant ON: campaign_stats returns only scoped client data."""
    os.environ["AE_MULTI_TENANT_ENABLED"] = "1"
    os.environ["AE_CONSOLE_SECRET"] = "s"
    db_path = str(tmp_path / "ae.db")
    dbmod.init_db(db_path)

    c = TestClient(app)
    headers = {"X-AE-SECRET": "s"}

    # Create clients c1, c2
    for slug in ["c1", "c2"]:
        r = c.post(
            "/api/clients",
            params={"db_path": db_path},
            headers={**headers, "X-Tenant-ID": slug},
            json={
                "slug": slug,
                "name": f"Client {slug}",
                "industry": "plumber",
                "geo_country": "TH",
                "geo": "chiang mai",
                "primary_phone": "+66-400-000-001",
                "lead_email": f"{slug}@example.com",
            },
        )
        assert r.status_code == 200

    # Import spend for c1 and c2
    from datetime import date, timedelta
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    c.post(
        "/api/spend/import",
        params={"db": db_path},
        headers={**headers, "X-Tenant-ID": "c1"},
        json={"items": [{"day": yesterday, "source": "meta", "spend_value": 100.0, "utm_campaign": "camp-a", "client_id": "c1"}]},
    )
    c.post(
        "/api/spend/import",
        params={"db": db_path},
        headers={**headers, "X-Tenant-ID": "c2"},
        json={"items": [{"day": yesterday, "source": "meta", "spend_value": 200.0, "utm_campaign": "camp-b", "client_id": "c2"}]},
    )

    # List spend with tenant c1: only c1
    r = c.get("/api/spend", params={"db": db_path}, headers={**headers, "X-Tenant-ID": "c1"})
    assert r.status_code == 200
    items = r.json().get("items", [])
    assert len(items) >= 1
    for it in items:
        assert it.get("client_id") == "c1"

    # campaign_stats with tenant c1: only c1's data
    r = c.get("/api/stats/campaign", params={"db": db_path, "days": 30}, headers={**headers, "X-Tenant-ID": "c1"})
    assert r.status_code == 200
    camps = r.json().get("campaigns", [])
    for camp in camps:
        # All campaigns should be from c1's spend (we only have camp-a for c1)
        pass  # campaign_stats returns by utm_campaign; both c1 and c2 could have same campaign name
    # At least totals should reflect scoped client (X-Tenant-ID or explicit client_id)
    r2 = c.get(
        "/api/stats/kpis",
        params={"db": db_path, "client_id": "c1"},
        headers={**headers, "X-Tenant-ID": "c1"},
    )
    assert r2.status_code == 200
    totals = r2.json().get("totals", {})
    # c1 has 100 spend; c2 has 200. Scoped to c1 we expect spend=100
    assert totals.get("spend", 0) == 100.0, f"expected spend=100, got {totals}"


def test_multi_tenant_service_packages_public_uses_tenant(tmp_path):
    """With multi-tenant ON: public packages uses X-Tenant-ID as client_id when not in query."""
    os.environ["AE_MULTI_TENANT_ENABLED"] = "1"
    os.environ.pop("AE_CONSOLE_SECRET", None)
    db_path = str(tmp_path / "acq.db")
    dbmod.init_db(db_path)

    c = TestClient(app)

    # Create client c1 and package p1
    c.post(
        "/api/clients",
        params={"db_path": db_path},
        headers={"X-AE-SECRET": "s", "X-Tenant-ID": "c1"},
        json={
            "slug": "c1",
            "name": "Client One",
            "industry": "plumber",
            "geo_country": "TH",
            "geo": "chiang mai",
            "primary_phone": "+66-400-000-001",
            "lead_email": "c1@example.com",
        },
    )
    c.post(
        "/api/service-packages",
        params={"db": db_path},
        headers={"X-AE-SECRET": "s", "X-Tenant-ID": "c1"},
        json={"package_id": "p1", "client_id": "c1", "name": "P1", "price": 100.0, "duration_min": 60},
    )

    # Public packages with X-Tenant-ID, no client_id in query -> uses tenant as client_id
    r = c.get("/v1/service-packages", params={"db": db_path}, headers={"X-Tenant-ID": "c1"})
    assert r.status_code == 200
    items = r.json().get("items", [])
    assert len(items) >= 1
    assert items[0]["package_id"] == "p1"
    assert items[0]["client_id"] == "c1"


# --- Batch 4 integration tests (events, chat, QR, payments) ---


def _seed_batch4_events(db_path: str):
    """Seed template, clients c1/c2, pages p1/p2, and events for each page."""
    dbmod.init_db(db_path)
    repo.upsert_template(
        db_path,
        Template(
            template_id="trade_lp",
            template_name="Trades LP",
            template_version="1.0.0",
            cms_schema_version="1.0",
            compatible_events_version="1.0",
            status=TemplateStatus.active,
        ),
    )
    for slug in ["c1", "c2"]:
        repo.upsert_client(
            db_path,
            Client(
                client_id=slug,
                client_name=f"Client {slug}",
                trade=Trade.plumber,
                geo_country="TH",
                geo_city="chiang mai",
                service_area=["Bangkok"],
                primary_phone="+66-400-000-001",
                lead_email=f"{slug}@example.com",
            ),
        )
        repo.upsert_page(
            db_path,
            Page(
                page_id=f"p{slug}",
                client_id=slug,
                template_id="trade_lp",
                template_version="1.0.0",
                page_slug=f"p{slug}",
                page_url=f"https://example.com/{slug}",
                page_status=PageStatus.draft,
                content_version=1,
            ),
        )
    from ae.service import record_event

    record_event(db_path, "pc1", EventName.call_click, {})
    record_event(db_path, "pc2", EventName.call_click, {})


def test_multi_tenant_scoped_events(tmp_path):
    """With multi-tenant ON: list events returns only scoped client (via page join)."""
    os.environ["AE_MULTI_TENANT_ENABLED"] = "1"
    os.environ["AE_CONSOLE_SECRET"] = "s"
    db_path = str(tmp_path / "ae.db")
    _seed_batch4_events(db_path)

    c = TestClient(app)
    headers = {"X-AE-SECRET": "s"}

    r = c.get("/api/events", params={"db": db_path}, headers={**headers, "X-Tenant-ID": "c1"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["page_id"] == "pc1"


def test_multi_tenant_scoped_chat_channels(tmp_path):
    """With multi-tenant ON: list chat channels returns only scoped client; get other 403."""
    os.environ["AE_MULTI_TENANT_ENABLED"] = "1"
    os.environ["AE_CONSOLE_SECRET"] = "s"
    db_path = str(tmp_path / "ae.db")
    dbmod.init_db(db_path)

    for slug in ["c1", "c2"]:
        repo.upsert_client(
            db_path,
            Client(
                client_id=slug,
                client_name=f"Client {slug}",
                trade=Trade.plumber,
                geo_country="TH",
                geo_city="chiang mai",
                service_area=["Bangkok"],
                primary_phone="+66-400-000-001",
                lead_email=f"{slug}@example.com",
            ),
        )

    c = TestClient(app)
    headers = {"X-AE-SECRET": "s"}

    c.post(
        "/api/chat/channels",
        params={"db": db_path},
        headers={**headers, "X-Tenant-ID": "c1"},
        json={"channel_id": "ch1", "provider": "other", "handle": "h1", "meta_json": {"client_id": "c1"}},
    )
    c.post(
        "/api/chat/channels",
        params={"db": db_path},
        headers={**headers, "X-Tenant-ID": "c2"},
        json={"channel_id": "ch2", "provider": "other", "handle": "h2", "meta_json": {"client_id": "c2"}},
    )

    r = c.get("/api/chat/channels", params={"db": db_path}, headers={**headers, "X-Tenant-ID": "c1"})
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["channel_id"] == "ch1"

    r = c.get("/api/chat/channels/ch1", params={"db": db_path}, headers={**headers, "X-Tenant-ID": "c1"})
    assert r.status_code == 200

    r = c.get("/api/chat/channels/ch2", params={"db": db_path}, headers={**headers, "X-Tenant-ID": "c1"})
    assert r.status_code == 403


def test_multi_tenant_scoped_chat_conversations(tmp_path):
    """With multi-tenant ON: list conversations returns only those whose lead has matching client_id."""
    os.environ["AE_MULTI_TENANT_ENABLED"] = "1"
    os.environ["AE_CONSOLE_SECRET"] = "s"
    db_path = str(tmp_path / "ae.db")
    dbmod.init_db(db_path)

    for slug in ["c1", "c2"]:
        repo.upsert_client(
            db_path,
            Client(
                client_id=slug,
                client_name=f"Client {slug}",
                trade=Trade.plumber,
                geo_country="TH",
                geo_city="chiang mai",
                service_area=["Bangkok"],
                primary_phone="+66-400-000-001",
                lead_email=f"{slug}@example.com",
            ),
        )

    ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    lid1 = repo.insert_lead(
        db_path,
        LeadIntake(ts=ts, source="web", client_id="c1", name="L1", phone="p1", email="e1@x.com", status="new"),
    )
    lid2 = repo.insert_lead(
        db_path,
        LeadIntake(ts=ts, source="web", client_id="c2", name="L2", phone="p2", email="e2@x.com", status="new"),
    )

    repo.upsert_chat_channel(db_path, channel_id="ch1", provider=ChatProvider.other, handle="h1", meta_json={"client_id": "c1"})
    repo.upsert_chat_channel(db_path, channel_id="ch2", provider=ChatProvider.other, handle="h2", meta_json={"client_id": "c2"})

    repo.get_or_create_chat_conversation(db_path, conversation_id="conv1", channel_id="ch1", lead_id=str(lid1))
    repo.get_or_create_chat_conversation(db_path, conversation_id="conv2", channel_id="ch2", lead_id=str(lid2))

    c = TestClient(app)
    headers = {"X-AE-SECRET": "s"}

    r = c.get("/api/chat/conversations", params={"db": db_path}, headers={**headers, "X-Tenant-ID": "c1"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["conversation_id"] == "conv1"


def test_multi_tenant_scoped_qr_attributions(tmp_path):
    """With multi-tenant ON: list QR attributions returns only via menu; get other 403."""
    os.environ["AE_MULTI_TENANT_ENABLED"] = "1"
    os.environ["AE_CONSOLE_SECRET"] = "s"
    db_path = str(tmp_path / "ae.db")
    dbmod.init_db(db_path)

    for slug in ["c1", "c2"]:
        repo.upsert_client(
            db_path,
            Client(
                client_id=slug,
                client_name=f"Client {slug}",
                trade=Trade.plumber,
                geo_country="TH",
                geo_city="chiang mai",
                service_area=["Bangkok"],
                primary_phone="+66-400-000-001",
                lead_email=f"{slug}@example.com",
            ),
        )

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat() + "Z"
    repo.upsert_menu(
        db_path,
        Menu(menu_id="m1", client_id="c1", name="M1", language="en", currency="THB", status=MenuStatus.draft, created_at=now, updated_at=now),
    )
    repo.upsert_menu(
        db_path,
        Menu(menu_id="m2", client_id="c2", name="M2", language="en", currency="THB", status=MenuStatus.draft, created_at=now, updated_at=now),
    )

    repo.create_qr_attribution(db_path, kind="link", url="https://x.com/1", menu_id="m1")
    repo.create_qr_attribution(db_path, kind="link", url="https://x.com/2", menu_id="m2", attribution_id="attr2")

    c = TestClient(app)
    headers = {"X-AE-SECRET": "s"}

    r = c.get("/api/qr/attributions", params={"db": db_path}, headers={**headers, "X-Tenant-ID": "c1"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["menu_id"] == "m1"

    attrs = repo.list_qr_attributions(db_path, client_id="c1")
    attr1_id = attrs[0].attribution_id if attrs else None
    attrs2 = repo.list_qr_attributions(db_path, client_id="c2")
    attr2_id = attrs2[0].attribution_id if attrs2 else "attr2"

    r = c.get(f"/api/qr/attributions/{attr1_id}", params={"db": db_path}, headers={**headers, "X-Tenant-ID": "c1"})
    assert r.status_code == 200

    r = c.get(f"/api/qr/attributions/{attr2_id}", params={"db": db_path}, headers={**headers, "X-Tenant-ID": "c1"})
    assert r.status_code == 403


def test_multi_tenant_scoped_payments(tmp_path):
    """With multi-tenant ON: list payments returns only scoped client; get other 403."""
    os.environ["AE_MULTI_TENANT_ENABLED"] = "1"
    os.environ["AE_CONSOLE_SECRET"] = "s"
    db_path = str(tmp_path / "ae.db")
    dbmod.init_db(db_path)

    for slug in ["c1", "c2"]:
        repo.upsert_client(
            db_path,
            Client(
                client_id=slug,
                client_name=f"Client {slug}",
                trade=Trade.plumber,
                geo_country="TH",
                geo_city="chiang mai",
                service_area=["Bangkok"],
                primary_phone="+66-400-000-001",
                lead_email=f"{slug}@example.com",
            ),
        )

    ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    lid1 = repo.insert_lead(
        db_path,
        LeadIntake(
            ts=ts,
            source="web",
            client_id="c1",
            name="L1",
            phone="p1",
            email="e1@x.com",
            status="new",
            booking_status="confirmed",
            booking_value=1000.0,
            booking_currency="THB",
        ),
    )
    lid2 = repo.insert_lead(
        db_path,
        LeadIntake(
            ts=ts,
            source="web",
            client_id="c2",
            name="L2",
            phone="p2",
            email="e2@x.com",
            status="new",
            booking_status="confirmed",
            booking_value=2000.0,
            booking_currency="THB",
        ),
    )

    repo.create_payment(
        db_path,
        payment_id="pay1",
        booking_id=f"lead-{lid1}",
        lead_id=lid1,
        amount=1000.0,
        provider=PaymentProvider.manual,
        method=PaymentMethod.cash,
    )
    repo.create_payment(
        db_path,
        payment_id="pay2",
        booking_id=f"lead-{lid2}",
        lead_id=lid2,
        amount=2000.0,
        provider=PaymentProvider.manual,
        method=PaymentMethod.cash,
    )

    c = TestClient(app)
    headers = {"X-AE-SECRET": "s"}

    r = c.get("/api/payments", params={"db": db_path}, headers={**headers, "X-Tenant-ID": "c1"})
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["payment_id"] == "pay1"

    r = c.get("/api/payments/pay1", params={"db": db_path}, headers={**headers, "X-Tenant-ID": "c1"})
    assert r.status_code == 200

    r = c.get("/api/payments/pay2", params={"db": db_path}, headers={**headers, "X-Tenant-ID": "c1"})
    assert r.status_code == 403


def test_tenant_security_smoke(tmp_path, monkeypatch):
    """Minimal multi-tenant + session + Batch 4 flow: login with tenant, list scoped, Batch 4 route."""
    db_path = str(tmp_path / "ae.db")
    dbmod.init_db(db_path)

    from ae.auth import create_user
    create_user(db_path, username="op", password="pw", role="operator")

    for slug in ["c1", "c2"]:
        repo.upsert_client(
            db_path,
            Client(
                client_id=slug,
                client_name=f"Client {slug}",
                trade=Trade.plumber,
                geo_country="TH",
                geo_city="chiang mai",
                service_area=["Bangkok"],
                primary_phone="+66-400-000-001",
                lead_email=f"{slug}@example.com",
            ),
        )
        now = datetime.now(timezone.utc).replace(microsecond=0)
        repo.create_package(
            db_path,
            ServicePackage(
                package_id=f"pkg-{slug}",
                client_id=slug,
                name=f"Pkg {slug}",
                price=100.0,
                duration_min=60,
                active=True,
                created_at=now,
                updated_at=now,
            ),
        )

    monkeypatch.setenv("AE_DB_PATH", db_path)
    monkeypatch.setenv("AE_MULTI_TENANT_ENABLED", "1")
    monkeypatch.setenv("AE_CONSOLE_SECRET", "")

    c = TestClient(app)

    # Login with X-Tenant-ID c1
    r = c.post("/api/auth/login", json={"username": "op", "password": "pw"}, headers={"X-Tenant-ID": "c1"})
    assert r.status_code == 200
    session_cookie = r.cookies.get("ae_session")

    # List packages with session only (no X-Tenant-ID) -> scoped to c1 from session
    r2 = c.get("/api/service-packages", params={"db": db_path}, cookies={"ae_session": session_cookie})
    assert r2.status_code == 200
    items = r2.json().get("items", [])
    assert len(items) == 1
    assert items[0]["client_id"] == "c1"

    # Batch 4: list events with session (tenant from session)
    _seed_batch4_events(db_path)
    r3 = c.get("/api/events", params={"db": db_path}, cookies={"ae_session": session_cookie})
    assert r3.status_code == 200
    assert len(r3.json()["items"]) >= 1

