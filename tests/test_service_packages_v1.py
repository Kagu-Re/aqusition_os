import os
from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod, repo
from ae.models import Client, ServicePackage
from ae.enums import Trade
from datetime import datetime


def _seed(db_path: str):
    """Seed database with a test client."""
    dbmod.init_db(db_path)
    repo.upsert_client(db_path, Client(
        client_id="c1",
        client_name="Client One",
        trade=Trade.plumber,
        geo_country="th",
        geo_city="chiang_mai",
        service_area=["CM"],
        primary_phone="000",
        lead_email="a@example.com",
        status="live",
        hours=None,
        license_badges=[],
        price_anchor=None,
        brand_theme=None,
        notes_internal=None,
    ))


def test_service_package_create_and_get(tmp_path):
    """Test creating and retrieving a service package."""
    db_path = str(tmp_path / "t.db")
    _seed(db_path)
    os.environ.pop("AE_CONSOLE_SECRET", None)
    client = TestClient(app)

    # Create package
    r = client.post("/api/service-packages?db=" + db_path, json={
        "package_id": "pkg1",
        "client_id": "c1",
        "name": "60 min session",
        "price": 800.0,
        "duration_min": 60,
        "addons": ["Home visit +200", "Same-day +150"],
        "active": True,
        "meta_json": {"category": "massage"}
    })
    assert r.status_code == 200
    body = r.json()
    assert body["package"]["package_id"] == "pkg1"
    assert body["package"]["name"] == "60 min session"
    assert body["package"]["price"] == 800.0
    assert body["package"]["duration_min"] == 60
    assert len(body["package"]["addons"]) == 2
    assert body["package"]["active"] is True

    # Get package
    r2 = client.get("/api/service-packages/pkg1?db=" + db_path)
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["package"]["package_id"] == "pkg1"
    assert body2["package"]["name"] == "60 min session"


def test_service_package_list_with_filters(tmp_path):
    """Test listing packages with filters."""
    db_path = str(tmp_path / "t.db")
    _seed(db_path)
    os.environ.pop("AE_CONSOLE_SECRET", None)
    client = TestClient(app)

    # Create multiple packages
    now = datetime.utcnow()
    pkg1 = ServicePackage(
        package_id="pkg1",
        client_id="c1",
        name="60 min session",
        price=800.0,
        duration_min=60,
        addons=[],
        active=True,
        meta_json={},
        created_at=now,
        updated_at=now,
    )
    pkg2 = ServicePackage(
        package_id="pkg2",
        client_id="c1",
        name="90 min session",
        price=1200.0,
        duration_min=90,
        addons=[],
        active=False,
        meta_json={},
        created_at=now,
        updated_at=now,
    )
    repo.create_package(db_path, pkg1)
    repo.create_package(db_path, pkg2)

    # List all packages
    r = client.get("/api/service-packages?db=" + db_path)
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2

    # List active only
    r2 = client.get("/api/service-packages?db=" + db_path + "&active=true")
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["count"] == 1
    assert body2["items"][0]["package_id"] == "pkg1"

    # List by client_id
    r3 = client.get("/api/service-packages?db=" + db_path + "&client_id=c1")
    assert r3.status_code == 200
    body3 = r3.json()
    assert body3["count"] == 2


def test_service_package_update(tmp_path):
    """Test updating a service package."""
    db_path = str(tmp_path / "t.db")
    _seed(db_path)
    os.environ.pop("AE_CONSOLE_SECRET", None)
    client = TestClient(app)

    # Create package
    now = datetime.utcnow()
    pkg = ServicePackage(
        package_id="pkg1",
        client_id="c1",
        name="60 min session",
        price=800.0,
        duration_min=60,
        addons=[],
        active=True,
        meta_json={},
        created_at=now,
        updated_at=now,
    )
    repo.create_package(db_path, pkg)

    # Update package
    r = client.put("/api/service-packages/pkg1?db=" + db_path, json={
        "name": "60 min premium session",
        "price": 900.0,
        "active": False
    })
    assert r.status_code == 200
    body = r.json()
    assert body["package"]["name"] == "60 min premium session"
    assert body["package"]["price"] == 900.0
    assert body["package"]["active"] is False
    assert body["package"]["duration_min"] == 60  # unchanged


def test_service_package_validation(tmp_path):
    """Test validation rules for service packages."""
    db_path = str(tmp_path / "t.db")
    _seed(db_path)
    os.environ.pop("AE_CONSOLE_SECRET", None)
    client = TestClient(app)

    # Test negative price (should fail)
    r = client.post("/api/service-packages?db=" + db_path, json={
        "package_id": "pkg1",
        "client_id": "c1",
        "name": "Test",
        "price": -100.0,
        "duration_min": 60,
    })
    assert r.status_code == 422  # Validation error

    # Test zero duration (should fail)
    r2 = client.post("/api/service-packages?db=" + db_path, json={
        "package_id": "pkg2",
        "client_id": "c1",
        "name": "Test",
        "price": 100.0,
        "duration_min": 0,
    })
    assert r2.status_code == 422  # Validation error


def test_service_package_not_found(tmp_path):
    """Test getting non-existent package."""
    db_path = str(tmp_path / "t.db")
    _seed(db_path)
    os.environ.pop("AE_CONSOLE_SECRET", None)
    client = TestClient(app)

    r = client.get("/api/service-packages/nonexistent?db=" + db_path)
    assert r.status_code == 404
    assert "package_not_found" in r.json()["detail"]


def test_service_package_repository_crud(tmp_path):
    """Test repository functions directly."""
    db_path = str(tmp_path / "t.db")
    _seed(db_path)

    now = datetime.utcnow()
    pkg = ServicePackage(
        package_id="pkg1",
        client_id="c1",
        name="60 min session",
        price=800.0,
        duration_min=60,
        addons=["Home visit +200"],
        active=True,
        meta_json={"category": "massage"},
        created_at=now,
        updated_at=now,
    )

    # Create
    created = repo.create_package(db_path, pkg)
    assert created.package_id == "pkg1"
    assert created.price == 800.0
    assert len(created.addons) == 1

    # Get
    retrieved = repo.get_package(db_path, "pkg1")
    assert retrieved is not None
    assert retrieved.name == "60 min session"
    assert retrieved.active is True

    # List
    all_packages = repo.list_packages(db_path, client_id="c1")
    assert len(all_packages) == 1
    assert all_packages[0].package_id == "pkg1"

    # List active only
    active_packages = repo.list_packages(db_path, client_id="c1", active=True)
    assert len(active_packages) == 1

    # Update
    updated_pkg = ServicePackage(
        package_id="pkg1",
        client_id="c1",
        name="60 min premium session",
        price=900.0,
        duration_min=60,
        addons=[],
        active=False,
        meta_json={},
        created_at=created.created_at,
        updated_at=datetime.utcnow(),
    )
    updated = repo.update_package(db_path, updated_pkg)
    assert updated.name == "60 min premium session"
    assert updated.price == 900.0
    assert updated.active is False
