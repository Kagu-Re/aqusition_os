"""API key flow integration tests.

Verifies tenant-scoped API keys on public endpoints: X-AE-API-KEY resolves
tenant, leads/packages are scoped, invalid key falls back to X-Tenant-ID or 400.
"""
import os
import pytest

pytestmark = pytest.mark.tenant
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from ae.console_app import app
from ae.db import init_db
from ae.api_keys import create_api_key
from ae import repo
from ae.models import Client, ServicePackage
from ae.enums import Trade


def test_api_key_resolves_tenant_for_lead(tmp_path, monkeypatch):
    """create_api_key for c1; POST /lead with X-AE-API-KEY stores lead with client_id c1."""
    db_path = str(tmp_path / "ae.db")
    init_db(db_path)

    repo.upsert_client(
        db_path,
        Client(
            client_id="c1",
            client_name="Client 1",
            trade=Trade.plumber,
            geo_country="TH",
            geo_city="chiang mai",
            service_area=["Bangkok"],
            primary_phone="+66-400-000-001",
            lead_email="c1@example.com",
        ),
    )

    raw_key = create_api_key(db_path, "c1", "default")

    monkeypatch.setenv("AE_DB_PATH", db_path)
    monkeypatch.setenv("AE_MULTI_TENANT_ENABLED", "1")

    c = TestClient(app)

    r = c.post(
        "/lead",
        params={"db": db_path},
        headers={"X-AE-API-KEY": raw_key},
        json={"name": "Test Lead", "email": "test@example.com", "phone": "+66123456789"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    lead_id = body.get("lead_id")
    assert lead_id is not None

    # Verify lead has client_id c1
    leads = repo.list_leads(db_path, client_id="c1", limit=10)
    assert len(leads) >= 1
    assert any(l.lead_id == lead_id for l in leads)
    lead = next(l for l in leads if l.lead_id == lead_id)
    assert lead.client_id == "c1"


def test_api_key_on_service_packages(tmp_path, monkeypatch):
    """Same key; GET /v1/service-packages with X-AE-API-KEY, no client_id in query -> c1 only."""
    db_path = str(tmp_path / "ae.db")
    init_db(db_path)

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
                name=f"Package {slug}",
                price=100.0,
                duration_min=60,
                active=True,
                created_at=now,
                updated_at=now,
            ),
        )

    raw_key = create_api_key(db_path, "c1", "default")

    monkeypatch.setenv("AE_DB_PATH", db_path)
    monkeypatch.setenv("AE_MULTI_TENANT_ENABLED", "1")

    c = TestClient(app)

    # No client_id in query, only X-AE-API-KEY
    r = c.get(
        "/v1/service-packages",
        params={"db": db_path},
        headers={"X-AE-API-KEY": raw_key},
    )
    assert r.status_code == 200
    items = r.json().get("items", [])
    assert len(items) == 1
    assert items[0]["client_id"] == "c1"
    assert items[0]["package_id"] == "pkg-c1"


def test_invalid_api_key(tmp_path, monkeypatch):
    """Bogus X-AE-API-KEY: request proceeds with X-Tenant-ID or 400 if client_id required."""
    db_path = str(tmp_path / "ae.db")
    init_db(db_path)

    repo.upsert_client(
        db_path,
        Client(
            client_id="c1",
            client_name="Client 1",
            trade=Trade.plumber,
            geo_country="TH",
            geo_city="chiang mai",
            service_area=["Bangkok"],
            primary_phone="+66-400-000-001",
            lead_email="c1@example.com",
        ),
    )
    now = datetime.now(timezone.utc).replace(microsecond=0)
    repo.create_package(
        db_path,
        ServicePackage(
            package_id="pkg-c1",
            client_id="c1",
            name="Package c1",
            price=100.0,
            duration_min=60,
            active=True,
            created_at=now,
            updated_at=now,
        ),
    )

    monkeypatch.setenv("AE_DB_PATH", db_path)
    monkeypatch.setenv("AE_MULTI_TENANT_ENABLED", "1")

    c = TestClient(app)

    # Invalid key, no X-Tenant-ID: /v1/service-packages requires client_id or tenant
    r = c.get(
        "/v1/service-packages",
        params={"db": db_path},
        headers={"X-AE-API-KEY": "bogus_invalid_key_123"},
    )
    # Without valid key or X-Tenant-ID, scoped is None -> 400 client_id required
    assert r.status_code == 400
    assert "client_id" in (r.json().get("detail") or "").lower()

    # Invalid key WITH X-Tenant-ID: uses header
    r2 = c.get(
        "/v1/service-packages",
        params={"db": db_path},
        headers={"X-AE-API-KEY": "bogus_invalid_key_123", "X-Tenant-ID": "c1"},
    )
    assert r2.status_code == 200
    items = r2.json().get("items", [])
    assert len(items) == 1
    assert items[0]["client_id"] == "c1"
