"""Tests for publisher theme (template_style / data-theme) support."""

from pathlib import Path

from ae.adapters.publisher_tailwind_static import TailwindStaticSitePublisher


def _minimal_payload(extra=None):
    """Minimal valid payload for publishing."""
    p = {
        "page_id": "test-theme-page",
        "headline": "Test Headline",
        "subheadline": "Test subheadline",
        "cta_primary": "Book now",
        "cta_secondary": "Get quote",
        "sections": [
            {"type": "amenities", "items": ["Item 1"]},
            {"type": "testimonials", "items": ["Testimonial 1"]},
            {"type": "faq", "items": ["FAQ 1"]},
        ],
        "template_type": "service",
    }
    if extra:
        p.update(extra)
    return p


def test_publisher_sets_data_theme_from_payload(tmp_path):
    """Payload with template_style='spa' produces data-theme='spa' on html."""
    payload = _minimal_payload({"template_style": "spa"})
    pub = TailwindStaticSitePublisher(out_dir=str(tmp_path))
    result = pub.publish("test-theme-page", payload, {"db_path": "test.db"})
    assert result.ok is True
    html = (tmp_path / "test-theme-page" / "index.html").read_text(encoding="utf-8")
    assert 'data-theme="spa"' in html


def test_publisher_default_theme_when_missing(tmp_path):
    """No template_style produces data-theme='minimal' (default)."""
    payload = _minimal_payload()
    assert "template_style" not in payload
    pub = TailwindStaticSitePublisher(out_dir=str(tmp_path))
    result = pub.publish("test-theme-page", payload, {"db_path": "test.db"})
    assert result.ok is True
    html = (tmp_path / "test-theme-page" / "index.html").read_text(encoding="utf-8")
    assert 'data-theme="minimal"' in html


def test_publisher_invalid_theme_fallback(tmp_path):
    """Invalid template_style falls back to default (minimal)."""
    payload = _minimal_payload({"template_style": "invalid_theme"})
    pub = TailwindStaticSitePublisher(out_dir=str(tmp_path))
    result = pub.publish("test-theme-page", payload, {"db_path": "test.db"})
    assert result.ok is True
    html = (tmp_path / "test-theme-page" / "index.html").read_text(encoding="utf-8")
    assert 'data-theme="minimal"' in html
