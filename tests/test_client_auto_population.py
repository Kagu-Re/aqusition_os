"""Tests for client auto-population from trade templates."""

import pytest
import tempfile
import os
from ae.models import Client
from ae.enums import Trade, BusinessModel, ClientStatus
from ae.client_service import (
    apply_trade_template_to_client,
    generate_default_service_config,
    create_default_packages_from_template
)
from ae import repo


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    from ae import db
    db.init_db(path)
    yield path
    os.unlink(path)


def test_apply_trade_template_populates_empty_fields():
    """Test that trade template populates empty Tier 2 fields."""
    client = Client(
        client_id="test-massage",
        client_name="Test Massage",
        trade=Trade.massage,
        geo_country="TH",
        geo_city="Bangkok",
        service_area=["Bangkok"],
        primary_phone="+66-80-000-0000",
        lead_email="test@example.com",
        # Empty Tier 2 fields
        hours=None,
        license_badges=[],
        price_anchor=None,
        brand_theme=None,
    )
    
    enhanced = apply_trade_template_to_client(client)
    
    assert enhanced.hours is not None
    assert len(enhanced.license_badges) > 0
    assert enhanced.price_anchor is not None
    assert enhanced.brand_theme is not None


def test_apply_trade_template_preserves_existing_values():
    """Test that existing values are not overwritten."""
    client = Client(
        client_id="test-massage",
        client_name="Test Massage",
        trade=Trade.massage,
        geo_country="TH",
        geo_city="Bangkok",
        service_area=["Bangkok"],
        primary_phone="+66-80-000-0000",
        lead_email="test@example.com",
        hours="Custom Hours: 10am-10pm",
        license_badges=["Custom License"],
        price_anchor="Custom: ฿500",
        brand_theme="Custom Theme",
    )
    
    enhanced = apply_trade_template_to_client(client)
    
    assert enhanced.hours == "Custom Hours: 10am-10pm"
    assert enhanced.license_badges == ["Custom License"]
    assert enhanced.price_anchor == "Custom: ฿500"
    assert enhanced.brand_theme == "Custom Theme"


def test_generate_default_service_config():
    """Test service_config_json generation from template."""
    client = Client(
        client_id="test-massage",
        client_name="Test Massage Spa",
        trade=Trade.massage,
        geo_country="TH",
        geo_city="Bangkok",
        service_area=["Bangkok"],
        primary_phone="+66-80-000-0000",
        lead_email="test@example.com",
        hours="Mon-Sun 9am-9pm",
        price_anchor="Starting from ฿800",
    )
    
    config = generate_default_service_config(client)
    
    assert "default_amenities" in config or "custom_amenities" in config
    assert "default_testimonials" in config or "custom_testimonials" in config
    assert "default_faq" in config or "custom_faq" in config
    assert "default_cta_primary" in config or "custom_cta_primary" in config
    
    # Check placeholders were replaced
    if "default_testimonials" in config:
        for testimonial in config["default_testimonials"]:
            assert "{service_area[0]}" not in testimonial
            assert "{price_anchor}" not in testimonial


def test_create_default_packages_for_fixed_price(temp_db):
    """Test default packages are created for fixed_price clients."""
    client = Client(
        client_id="test-massage-fixed",
        client_name="Test Massage",
        trade=Trade.massage,
        business_model=BusinessModel.fixed_price,
        geo_country="TH",
        geo_city="Bangkok",
        service_area=["Bangkok"],
        primary_phone="+66-80-000-0000",
        lead_email="test@example.com",
    )
    
    # Create client first
    repo.upsert_client(temp_db, client, apply_defaults=False)
    
    # Create packages
    packages = create_default_packages_from_template(temp_db, client)
    
    assert len(packages) > 0
    assert all(pkg.client_id == client.client_id for pkg in packages)
    assert all(pkg.active for pkg in packages)


def test_create_default_packages_skips_quote_based(temp_db):
    """Test packages are not created for quote_based clients."""
    client = Client(
        client_id="test-plumber",
        client_name="Test Plumber",
        trade=Trade.plumber,
        business_model=BusinessModel.quote_based,
        geo_country="AU",
        geo_city="Sydney",
        service_area=["Sydney"],
        primary_phone="+61-400-000-000",
        lead_email="test@example.com",
    )
    
    repo.upsert_client(temp_db, client, apply_defaults=False)
    
    packages = create_default_packages_from_template(temp_db, client)
    
    assert len(packages) == 0


def test_create_default_packages_idempotent(temp_db):
    """Test package creation is idempotent (doesn't create duplicates)."""
    client = Client(
        client_id="test-massage-idempotent",
        client_name="Test Massage",
        trade=Trade.massage,
        business_model=BusinessModel.fixed_price,
        geo_country="TH",
        geo_city="Bangkok",
        service_area=["Bangkok"],
        primary_phone="+66-80-000-0000",
        lead_email="test@example.com",
    )
    
    repo.upsert_client(temp_db, client, apply_defaults=False)
    
    # Create packages first time
    packages1 = create_default_packages_from_template(temp_db, client)
    count1 = len(packages1)
    
    # Try to create again
    packages2 = create_default_packages_from_template(temp_db, client)
    count2 = len(packages2)
    
    assert count1 > 0
    assert count2 == 0  # Should not create duplicates


def test_upsert_client_with_defaults(temp_db):
    """Test upsert_client with apply_defaults=True."""
    client = Client(
        client_id="test-massage-auto",
        client_name="Test Massage",
        trade=Trade.massage,
        business_model=BusinessModel.fixed_price,
        geo_country="TH",
        geo_city="Bangkok",
        service_area=["Bangkok"],
        primary_phone="+66-80-000-0000",
        lead_email="test@example.com",
    )
    
    # Upsert with defaults
    repo.upsert_client(temp_db, client, apply_defaults=True)
    
    # Retrieve and verify defaults applied
    stored = repo.get_client(temp_db, client_id=client.client_id)
    assert stored is not None
    assert stored.hours is not None
    assert len(stored.license_badges) > 0
    assert stored.price_anchor is not None
    assert stored.brand_theme is not None
    
    # Verify packages were created
    from ae.repo_service_packages import list_packages
    packages = list_packages(temp_db, client_id=client.client_id, active=True)
    assert len(packages) > 0
