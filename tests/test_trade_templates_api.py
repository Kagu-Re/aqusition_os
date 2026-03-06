"""Integration tests for trade templates API."""

import os
from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod


def test_get_trade_templates_list(tmp_path):
    """GET /api/trade-templates returns list with massage, plumber."""
    os.environ["AE_CONSOLE_SECRET"] = "s"
    c = TestClient(app)
    r = c.get("/api/trade-templates", headers={"X-AE-SECRET": "s"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "items" in data
    assert data["count"] >= 8
    trades = [x["trade"] for x in data["items"]]
    assert "massage" in trades
    assert "plumber" in trades
    assert "roofing" in trades


def test_get_trade_template_by_trade(tmp_path):
    """GET /api/trade-templates/massage returns full template with default_packages."""
    os.environ["AE_CONSOLE_SECRET"] = "s"
    c = TestClient(app)
    r = c.get("/api/trade-templates/massage", headers={"X-AE-SECRET": "s"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "template" in data
    t = data["template"]
    assert "default_packages" in t
    assert len(t["default_packages"]) > 0
    assert "default_amenities" in t
    assert "price_anchor_formatted" in t


def test_get_trade_template_preview_geo(tmp_path):
    """GET /api/trade-templates/massage?geo=AU returns AU price anchor."""
    os.environ["AE_CONSOLE_SECRET"] = "s"
    c = TestClient(app)
    r = c.get(
        "/api/trade-templates/massage",
        params={"geo": "AU"},
        headers={"X-AE-SECRET": "s"},
    )
    assert r.status_code == 200, r.text
    t = r.json()["template"]
    anchor = t["price_anchor_formatted"]
    assert "A$" in anchor or "$" in anchor
    assert "Starting from" in anchor


def test_get_trade_template_not_found(tmp_path):
    """GET /api/trade-templates/invalid returns 404."""
    os.environ["AE_CONSOLE_SECRET"] = "s"
    c = TestClient(app)
    r = c.get("/api/trade-templates/invalid-trade", headers={"X-AE-SECRET": "s"})
    assert r.status_code == 404


def test_reapply_template_updates_client(tmp_path):
    """POST reapply-template refreshes client hours and amenities."""
    db_path = str(tmp_path / "ae.db")
    dbmod.init_db(db_path)
    os.environ["AE_CONSOLE_SECRET"] = "s"
    c = TestClient(app)
    payload = {
        "slug": "reapply-test",
        "name": "Reapply Test Massage",
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
    client = r.json()["client"]
    assert client["hours"]  # Template applied on create

    # Overwrite with custom values
    from ae import repo
    from ae.models import Client
    from ae.enums import Trade, BusinessModel, ClientStatus
    stored = repo.get_client(db_path, "reapply-test")
    stored.hours = "Custom 24/7"
    stored.service_config_json = stored.service_config_json or {}
    stored.service_config_json["custom_amenities"] = ["Custom only"]
    repo.upsert_client(db_path, stored, apply_defaults=False)

    # Reapply template
    r = c.post(
        "/api/clients/reapply-test/reapply-template",
        params={"db_path": db_path},
        headers={"X-AE-SECRET": "s"},
        json={"create_packages": False},
    )
    assert r.status_code == 200
    updated = r.json()["client"]
    assert updated["hours"] == "Mon-Sun 9am-9pm"  # Massage template default
    assert "default_amenities" in (updated.get("service_config_json") or {})
    assert (updated.get("service_config_json") or {}).get("default_amenities")
