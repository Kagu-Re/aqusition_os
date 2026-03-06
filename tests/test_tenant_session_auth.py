"""Session-scoped tenant auth integration tests.

Verifies that when a user logs in with X-Tenant-ID, subsequent requests are bound
to that tenant (session cookie only). X-Tenant-ID mismatch returns 403.
"""
import os
import pytest

pytestmark = pytest.mark.tenant
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from ae.console_app import app
from ae.db import init_db
from ae.auth import create_user
from ae import repo
from ae.models import Client, ServicePackage
from ae.enums import Trade


def test_login_stores_tenant_id(tmp_path, monkeypatch):
    """Login with X-Tenant-ID stores tenant in session; subsequent request with cookie only uses it."""
    db_path = str(tmp_path / "ae.db")
    init_db(db_path)
    create_user(db_path, username="op", password="pw123", role="operator")

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

    monkeypatch.setenv("AE_DB_PATH", db_path)
    monkeypatch.setenv("AE_MULTI_TENANT_ENABLED", "1")
    monkeypatch.setenv("AE_CONSOLE_SECRET", "")

    c = TestClient(app)

    # Login with X-Tenant-ID: c1 — session stores tenant_id
    r = c.post(
        "/api/auth/login",
        json={"username": "op", "password": "pw123"},
        headers={"X-Tenant-ID": "c1"},
    )
    assert r.status_code == 200
    session_cookie = r.cookies.get("ae_session")
    assert session_cookie

    # GET /api/service-packages with session cookie only (no X-Tenant-ID)
    # Should return only c1's packages (tenant from session)
    r2 = c.get(
        "/api/service-packages",
        params={"db": db_path},
        cookies={"ae_session": session_cookie},
    )
    assert r2.status_code == 200
    items = r2.json().get("items", [])
    assert len(items) == 1
    assert items[0]["client_id"] == "c1"
    assert items[0]["package_id"] == "pkg-c1"


def test_x_tenant_id_mismatch_403(tmp_path, monkeypatch):
    """Login with X-Tenant-ID: c1; request with X-Tenant-ID: c2 → 403 tenant_mismatch."""
    db_path = str(tmp_path / "ae.db")
    init_db(db_path)
    create_user(db_path, username="op", password="pw123", role="operator")

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

    monkeypatch.setenv("AE_DB_PATH", db_path)
    monkeypatch.setenv("AE_MULTI_TENANT_ENABLED", "1")
    monkeypatch.setenv("AE_CONSOLE_SECRET", "")

    c = TestClient(app)

    r = c.post(
        "/api/auth/login",
        json={"username": "op", "password": "pw123"},
        headers={"X-Tenant-ID": "c1"},
    )
    assert r.status_code == 200
    session_cookie = r.cookies.get("ae_session")

    # Request with X-Tenant-ID: c2 — session has c1, mismatch
    r2 = c.get(
        "/api/service-packages",
        params={"db": db_path},
        cookies={"ae_session": session_cookie},
        headers={"X-Tenant-ID": "c2"},
    )
    assert r2.status_code == 403
    assert r2.json().get("detail") == "tenant_mismatch"


def test_session_without_tenant_uses_header(tmp_path, monkeypatch):
    """Login without X-Tenant-ID (single-tenant); subsequent request with X-Tenant-ID uses header."""
    db_path = str(tmp_path / "ae.db")
    init_db(db_path)
    create_user(db_path, username="op", password="pw123", role="operator")

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
    monkeypatch.setenv("AE_CONSOLE_SECRET", "")

    c = TestClient(app)

    # Login without X-Tenant-ID — session has no tenant_id
    r = c.post("/api/auth/login", json={"username": "op", "password": "pw123"})
    assert r.status_code == 200
    session_cookie = r.cookies.get("ae_session")

    # Request with X-Tenant-ID: c1 — backward compat: header used when session has no tenant
    r2 = c.get(
        "/api/service-packages",
        params={"db": db_path},
        cookies={"ae_session": session_cookie},
        headers={"X-Tenant-ID": "c1"},
    )
    assert r2.status_code == 200
    items = r2.json().get("items", [])
    assert len(items) == 1
    assert items[0]["client_id"] == "c1"
