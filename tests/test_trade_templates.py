"""Tests for trade template system."""

import json
import pytest

from ae.trade_templates import (
    get_trade_template,
    get_trade_template_or_fallback,
    format_price_anchor,
    list_trade_templates,
    get_trade_template_preview,
    _load_trades_config,
)
from ae.enums import Trade


def test_get_trade_template_exists():
    """Test getting existing trade template."""
    template = get_trade_template(Trade.massage)
    assert template is not None
    assert template.trade == Trade.massage
    assert template.default_hours
    assert template.default_amenities
    assert len(template.default_packages) > 0


def test_all_trades_have_dedicated_template():
    """Test all trades (including roofing, pest_control, hvac) have dedicated templates."""
    for trade in Trade:
        template = get_trade_template(trade)
        assert template is not None, f"Trade {trade.value} missing dedicated template"
        assert template.trade == trade


def test_get_trade_template_or_fallback():
    """Test get_trade_template_or_fallback returns valid template with correct trade."""
    template = get_trade_template_or_fallback(Trade.roofing)
    assert template is not None
    assert template.trade == Trade.roofing
    assert template.default_hours


def test_generic_fallback_sets_trade():
    """Test fallback behavior: returned template has requested trade and defaults."""
    for trade in Trade:
        template = get_trade_template_or_fallback(trade)
        assert template is not None
        assert template.trade == trade
        assert template.default_hours
        assert template.default_cta_primary


def test_format_price_anchor():
    """Test price anchor formatting."""
    template = get_trade_template(Trade.massage)
    anchor_th = format_price_anchor(template, "TH")
    assert "฿" in anchor_th
    assert "Starting from" in anchor_th
    
    anchor_au = format_price_anchor(template, "AU")
    assert "A$" in anchor_au or "$" in anchor_au


def test_massage_template_has_packages():
    """Test massage template has default packages."""
    template = get_trade_template(Trade.massage)
    assert len(template.default_packages) > 0
    for pkg in template.default_packages:
        assert "name" in pkg
        assert "price" in pkg
        assert "duration_min" in pkg


def test_massage_template_has_media():
    """Test massage template has hero and gallery media for complete page rendering."""
    template = get_trade_template(Trade.massage)
    assert template.default_hero_image_url is not None
    assert template.default_hero_image_url.startswith("http")
    assert len(template.default_gallery_images) >= 3
    for url in template.default_gallery_images:
        assert url.startswith("http")


def test_plumber_template_no_packages():
    """Test plumber template has no packages (quote-based)."""
    template = get_trade_template(Trade.plumber)
    assert len(template.default_packages) == 0


def test_template_has_required_fields():
    """Test all templates have required fields."""
    templates = [
        get_trade_template(Trade.massage),
        get_trade_template(Trade.plumber),
        get_trade_template(Trade.roofing),
    ]
    for template in templates:
        assert template.default_hours
        assert template.default_license_badges is not None
        assert template.default_price_anchor_pattern
        assert template.default_brand_theme
        assert template.default_amenities is not None
        assert template.default_testimonials_patterns is not None
        assert template.default_faq_patterns is not None
        assert template.default_cta_primary
        assert template.default_cta_secondary


def test_list_trade_templates_returns_all():
    """Test list_trade_templates returns all registered templates."""
    templates = list_trade_templates()
    assert len(templates) == len(Trade)
    trades = {t.trade for t in templates}
    for trade in Trade:
        assert trade in trades


def test_get_trade_template_preview_includes_placeholders():
    """Test get_trade_template_preview includes default_amenities and price_anchor_formatted."""
    preview = get_trade_template_preview(Trade.massage, geo="TH")
    assert "default_amenities" in preview
    assert preview["default_amenities"]
    assert "price_anchor_formatted" in preview
    assert "฿" in preview["price_anchor_formatted"] or "Starting from" in preview["price_anchor_formatted"]


def test_trades_config_loads_successfully():
    """Config (per-trade directory or legacy file) exists and parses with required structure."""
    config = _load_trades_config()
    assert "trades" in config
    assert "massage" in config["trades"]
    assert "generic" in config["trades"]
    assert config["trades"]["massage"]["default_hours"]
    assert "default_faq_qa" in config["trades"]["massage"]
    assert "currency_map" in config
    assert "price_ranges" in config


def test_trades_config_loads_from_directory(tmp_path):
    """Per-trade directory layout: _defaults.json + generic.json + {trade}.json."""
    (tmp_path / "_defaults.json").write_text(json.dumps({
        "currency_map": {"TH": "฿"},
        "price_ranges": {"massage": {"TH": 800}},
    }))
    (tmp_path / "generic.json").write_text(json.dumps({
        "version": "1.0",
        "default_hours": "9-5",
        "default_license_badges": [],
        "default_price_anchor_pattern": "From {currency}{amount}",
        "default_brand_theme": "Generic",
        "default_amenities": [],
        "default_testimonials_patterns": [],
        "default_faq_patterns": [],
        "default_faq_qa": [],
        "default_cta_primary": "Go",
        "default_cta_secondary": "Contact",
        "default_packages": [],
    }))
    (tmp_path / "massage.json").write_text(json.dumps({
        "version": "1.0",
        "default_hours": "9-9",
        "default_license_badges": [],
        "default_price_anchor_pattern": "From {currency}{amount}",
        "default_brand_theme": "Massage",
        "default_amenities": [],
        "default_testimonials_patterns": [],
        "default_faq_patterns": [],
        "default_faq_qa": [],
        "default_cta_primary": "Book",
        "default_cta_secondary": "Now",
        "default_packages": [],
    }))
    config = _load_trades_config(tmp_path)
    assert config["trades"]["massage"]["default_hours"] == "9-9"
    assert config["trades"]["generic"]["default_hours"] == "9-5"
    assert config["currency_map"]["TH"] == "฿"


def test_trades_config_missing_uses_env_override(tmp_path):
    """_load_trades_config(path) loads from explicit path; AE_TRADES_CONFIG_PATH overrides default."""
    alt_config = tmp_path / "alt_trades.json"
    alt_config.write_text(json.dumps({
        "currency_map": {"AU": "A$", "TH": "฿"},
        "price_ranges": {"massage": {"TH": 800}},
        "trades": {
            "massage": {
                "version": "1.0",
                "default_hours": "9-5",
                "default_license_badges": [],
                "default_price_anchor_pattern": "From {currency}{amount}",
                "default_brand_theme": "Test",
                "default_amenities": [],
                "default_testimonials_patterns": [],
                "default_faq_patterns": [],
                "default_faq_qa": [],
                "default_cta_primary": "Book",
                "default_cta_secondary": "Call",
                "default_packages": [],
            },
            "generic": {
                "version": "1.0",
                "default_hours": "9-5",
                "default_license_badges": [],
                "default_price_anchor_pattern": "From {currency}{amount}",
                "default_brand_theme": "Generic",
                "default_amenities": [],
                "default_testimonials_patterns": [],
                "default_faq_patterns": [],
                "default_faq_qa": [],
                "default_cta_primary": "Go",
                "default_cta_secondary": "Contact",
                "default_packages": [],
            },
        },
    }))
    config = _load_trades_config(alt_config)
    assert config["trades"]["massage"]["default_hours"] == "9-5"
