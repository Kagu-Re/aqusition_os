"""Integration tests for trade template package creation and sync."""

import os
import tempfile
from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod
from ae.models import Client
from ae.enums import Trade, BusinessModel
from ae.client_service import create_default_packages_from_template
from ae import repo
from ae.repo_service_packages import list_packages


def test_create_packages_includes_template_meta(tmp_path):
    """Packages created from template have source_template in meta_json."""
    db_path = str(tmp_path / "meta_test.db")
    dbmod.init_db(db_path)
    client = Client(
        client_id="meta-test",
        client_name="Meta Test",
        trade=Trade.massage,
        business_model=BusinessModel.fixed_price,
        geo_country="TH",
        geo_city="Bangkok",
        service_area=["Bangkok"],
        primary_phone="+66-80-000-0000",
        lead_email="test@example.com",
    )
    repo.upsert_client(db_path, client, apply_defaults=False)
    packages = create_default_packages_from_template(db_path, client)
    assert len(packages) > 0
    for pkg in packages:
        assert "source_template" in pkg.meta_json
        assert pkg.meta_json["source_template"] == "massage"
        assert "template_package_idx" in pkg.meta_json


def test_sync_packages_from_template_api(tmp_path):
    """POST sync-packages-from-template creates packages; idempotent when no changes."""
    db_path = str(tmp_path / "ae.db")
    dbmod.init_db(db_path)
    os.environ["AE_CONSOLE_SECRET"] = "s"
    c = TestClient(app)

    payload = {
        "slug": "sync-test",
        "name": "Sync Test Massage",
        "industry": "massage",
        "business_model": "fixed_price",
        "geo_country": "TH",
        "geo": "bangkok",
        "service_area": ["bangkok"],
        "primary_phone": "+66-80-000-0000",
        "lead_email": "test@example.com",
        "status": "draft",
    }
    r = c.post(
        "/api/clients",
        params={"db_path": db_path},
        headers={"X-AE-SECRET": "s"},
        json=payload,
    )
    assert r.status_code == 200
    packages_before = list_packages(db_path, client_id="sync-test", limit=50)
    assert len(packages_before) > 0

    r = c.post(
        "/api/clients/sync-test/sync-packages-from-template",
        params={"db_path": db_path},
        headers={"X-AE-SECRET": "s"},
        json={},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["created"] == 0  # Merge: packages exist, nothing to add

    r = c.post(
        "/api/clients/sync-test/sync-packages-from-template",
        params={"db_path": db_path},
        headers={"X-AE-SECRET": "s"},
        json={"overwrite": True},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["created"] > 0  # Overwrite: deleted and recreated
    packages_after = list_packages(db_path, client_id="sync-test", limit=50)
    assert len(packages_after) == data["created"]


def test_geo_aware_package_pricing():
    """Client with geo AU gets packages with AU-scaled prices."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    dbmod.init_db(path)
    try:
        client_au = Client(
            client_id="geo-au",
            client_name="Geo AU",
            trade=Trade.massage,
            business_model=BusinessModel.fixed_price,
            geo_country="AU",
            geo_city="Sydney",
            service_area=["Sydney"],
            primary_phone="+61-400-000-000",
            lead_email="test@example.com",
        )
        repo.upsert_client(path, client_au, apply_defaults=False)
        packages_au = create_default_packages_from_template(path, client_au)
        assert len(packages_au) > 0
        first_price_au = packages_au[0].price
        assert 50 <= first_price_au <= 150  # AU massage base ~80

        client_th = Client(
            client_id="geo-th",
            client_name="Geo TH",
            trade=Trade.massage,
            business_model=BusinessModel.fixed_price,
            geo_country="TH",
            geo_city="Bangkok",
            service_area=["Bangkok"],
            primary_phone="+66-80-000-0000",
            lead_email="test@example.com",
        )
        repo.upsert_client(path, client_th, apply_defaults=False)
        packages_th = create_default_packages_from_template(path, client_th)
        assert len(packages_th) > 0
        first_price_th = packages_th[0].price
        assert 500 <= first_price_th <= 1500  # TH massage base ~800

        assert first_price_th > first_price_au
    finally:
        os.unlink(path)
