"""Tests for publisher hero and gallery rendering."""

from pathlib import Path

from ae.adapters.publisher_tailwind_static import TailwindStaticSitePublisher


def _minimal_payload(extra=None):
    """Minimal valid payload for publishing."""
    p = {
        "page_id": "test-page",
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


def test_publisher_renders_hero_when_in_payload(tmp_path):
    """Payload with hero_image_url produces HTML containing img with that src."""
    hero_url = "https://images.unsplash.com/photo-test-hero?w=1200"
    payload = _minimal_payload({"hero_image_url": hero_url})
    pub = TailwindStaticSitePublisher(out_dir=str(tmp_path))
    result = pub.publish("test-page", payload, {"db_path": "test.db"})
    assert result.ok is True
    html_path = tmp_path / "test-page" / "index.html"
    assert html_path.exists()
    html = html_path.read_text(encoding="utf-8")
    assert f'src="{hero_url}"' in html or f'src="{hero_url}"' in html.replace("&quot;", '"')
    assert "<img" in html


def test_publisher_renders_gallery_when_in_payload(tmp_path):
    """Payload with gallery_images produces HTML with multiple img elements."""
    urls = [
        "https://images.unsplash.com/photo-1",
        "https://images.unsplash.com/photo-2",
        "https://images.unsplash.com/photo-3",
    ]
    payload = _minimal_payload({"gallery_images": urls})
    pub = TailwindStaticSitePublisher(out_dir=str(tmp_path))
    result = pub.publish("test-page", payload, {"db_path": "test.db"})
    assert result.ok is True
    html = (tmp_path / "test-page" / "index.html").read_text(encoding="utf-8")
    assert "Gallery" in html
    assert html.count("<img") >= 3
    for url in urls:
        assert url in html


def test_publisher_omits_hero_when_missing(tmp_path):
    """Payload without hero_image_url does not add hero img in hero section."""
    payload = _minimal_payload()
    assert "hero_image_url" not in payload
    pub = TailwindStaticSitePublisher(out_dir=str(tmp_path))
    result = pub.publish("test-page", payload, {"db_path": "test.db"})
    assert result.ok is True
    html = (tmp_path / "test-page" / "index.html").read_text(encoding="utf-8")
    # Should have headline but no hero img (no external image URL in hero area)
    assert "Test Headline" in html
    assert "object-cover" not in html or "Gallery" in html  # Gallery might add object-cover


def test_publisher_omits_gallery_when_empty(tmp_path):
    """Payload with empty gallery_images omits gallery section."""
    payload = _minimal_payload({"gallery_images": []})
    pub = TailwindStaticSitePublisher(out_dir=str(tmp_path))
    result = pub.publish("test-page", payload, {"db_path": "test.db"})
    assert result.ok is True
    html = (tmp_path / "test-page" / "index.html").read_text(encoding="utf-8")
    assert "Gallery" not in html


def test_publisher_faq_accordion(tmp_path):
    """Payload with faq Q&A items produces <details>, <summary>, and answer text."""
    answer_text = "We are open Monday through Friday 9am-6pm."
    payload = _minimal_payload({
        "sections": [
            {"type": "amenities", "items": ["Item 1"]},
            {"type": "testimonials", "items": ["Testimonial 1"]},
            {"type": "faq", "items": [{"q": "What are your hours?", "a": answer_text}]},
        ],
    })
    pub = TailwindStaticSitePublisher(out_dir=str(tmp_path))
    result = pub.publish("test-page", payload, {"db_path": "test.db"})
    assert result.ok is True
    html = (tmp_path / "test-page" / "index.html").read_text(encoding="utf-8")
    assert "<details" in html
    assert "lp-faq-summary" in html
    assert "What are your hours?" in html
    assert answer_text in html


def test_publisher_renders_review_cards(tmp_path):
    """Payload with reviews section produces blockquote/card markup and quote text."""
    payload = _minimal_payload({
        "sections": [
            {"type": "amenities", "items": ["A"]},
            {"type": "testimonials", "items": ["T"]},
            {
                "type": "reviews",
                "items": [
                    {"quote": "Best massage in Chiang Mai!", "author_name": "John D.", "rating": 5, "source": "google"},
                ],
            },
            {"type": "faq", "items": [{"q": "Q?", "a": "A"}]},
        ],
    })
    pub = TailwindStaticSitePublisher(out_dir=str(tmp_path))
    result = pub.publish("test-page", payload, {"db_path": "test.db"})
    assert result.ok is True
    html = (tmp_path / "test-page" / "index.html").read_text(encoding="utf-8")
    assert "lp-sticky-cta" in html
    assert "What Customers Say" in html
    assert "lp-reviews-scroll" in html
    assert "lp-review-slide" in html
    assert "lp-review-card" in html
    assert "Best massage in Chiang Mai!" in html
    assert "John D." in html
    assert "★★★★★" in html or "★" in html


def test_publisher_renders_contact_strip_when_client_has_phone(tmp_path):
    """Payload with client context that has primary_phone produces contact strip with tel: link."""
    from ae.models import Client
    from ae.enums import Trade, BusinessModel

    client = Client(
        client_id="contact-test",
        client_name="Test Spa",
        trade=Trade.massage,
        business_model=BusinessModel.fixed_price,
        geo_country="TH",
        geo_city="Chiang Mai",
        service_area=["Chiang Mai City"],
        primary_phone="+66-81-234-5678",
        lead_email="test@example.com",
    )
    payload = _minimal_payload({"sections": [
        {"type": "amenities", "items": ["A"]},
        {"type": "testimonials", "items": ["T"]},
        {"type": "faq", "items": [{"q": "Q?", "a": "A"}]},
    ]})
    pub = TailwindStaticSitePublisher(out_dir=str(tmp_path))
    result = pub.publish("test-page", payload, {"db_path": "test.db", "client": client})
    assert result.ok is True
    html = (tmp_path / "test-page" / "index.html").read_text(encoding="utf-8")
    assert "lp-hero-contact" in html
    assert "tel:" in html
    assert "+66" in html or "66812345678" in html


def test_contact_us_js_includes_intent_param_for_telegram(tmp_path):
    """Contact Us click handler includes start=intent_contact when provider is telegram."""
    payload = _minimal_payload({"client_id": "test-client"})
    pub = TailwindStaticSitePublisher(out_dir=str(tmp_path))
    result = pub.publish("test-page", payload, {"db_path": "test.db"})
    assert result.ok is True
    html = (tmp_path / "test-page" / "index.html").read_text(encoding="utf-8")
    assert "start=intent_contact" in html
    assert "chatChannel.provider" in html or "provider" in html
    assert "#contact" in html


def test_publisher_faq_at_bottom(tmp_path):
    """FAQ section appears after Packages and before Footer in HTML."""
    payload = _minimal_payload({
        "show_packages": True,
        "client_id": "test-client",
        "sections": [
            {"type": "amenities", "items": ["A"]},
            {"type": "testimonials", "items": ["T"]},
            {"type": "faq", "items": [{"q": "Q?", "a": "A"}]},
        ],
    })
    pub = TailwindStaticSitePublisher(out_dir=str(tmp_path))
    result = pub.publish("test-page", payload, {"db_path": "test.db"})
    assert result.ok is True
    html = (tmp_path / "test-page" / "index.html").read_text(encoding="utf-8")
    pkg_pos = html.find("packages-section")
    faq_pos = html.find("FAQ")  # FAQ heading in the section
    footer_pos = html.find("All rights reserved")  # Footer text
    assert pkg_pos != -1, "packages section should exist"
    assert faq_pos != -1, "FAQ section should exist"
    assert footer_pos != -1, "footer should exist"
    assert pkg_pos < faq_pos < footer_pos, "FAQ should be after Packages and before Footer"
