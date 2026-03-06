"""Tests for content stub media (hero, gallery) from trade templates."""

from ae.models import Client, Page
from ae.enums import Trade, BusinessModel
from ae.adapters.content_stub import StubContentAdapter
from ae.client_service import apply_trade_template_to_client, generate_default_service_config


def _massage_client(service_config=None):
    """Minimal massage client with template defaults applied."""
    client = Client(
        client_id="media-test-massage",
        client_name="Serenity Massage",
        trade=Trade.massage,
        business_model=BusinessModel.fixed_price,
        geo_country="TH",
        geo_city="Bangkok",
        service_area=["Bangkok"],
        primary_phone="+66-80-000-0000",
        lead_email="test@example.com",
    )
    client = apply_trade_template_to_client(client)
    client.service_config_json = generate_default_service_config(client)
    if service_config:
        client.service_config_json.update(service_config)
    return client


def _service_lp_page():
    """Page with service_lp template."""
    return Page(
        page_id="p-media-test",
        client_id="media-test-massage",
        template_id="service_lp",
        template_version="1.0",
        page_slug="serenity-massage",
        page_url="https://example.com/serenity-massage",
        page_status="draft",
        content_version=1,
    )


def test_content_stub_includes_hero_when_template_has_it():
    """Massage client with service_lp page returns hero_image_url in payload."""
    adapter = StubContentAdapter()
    client = _massage_client()
    page = _service_lp_page()
    payload = adapter.build("p-media-test", {"client": client, "page": page})
    assert "hero_image_url" in payload
    assert payload["hero_image_url"] is not None
    assert payload["hero_image_url"].startswith("http")


def test_content_stub_includes_gallery_when_template_has_it():
    """Massage client returns gallery_images with 3+ items."""
    adapter = StubContentAdapter()
    client = _massage_client()
    page = _service_lp_page()
    payload = adapter.build("p-media-test", {"client": client, "page": page})
    assert "gallery_images" in payload
    assert isinstance(payload["gallery_images"], list)
    assert len(payload["gallery_images"]) >= 3
    for url in payload["gallery_images"]:
        assert url.startswith("http")


def test_content_stub_custom_hero_overrides_template():
    """custom_hero_image_url in service_config overrides template default."""
    adapter = StubContentAdapter()
    custom_url = "https://example.com/custom-hero.jpg"
    client = _massage_client({"custom_hero_image_url": custom_url})
    page = _service_lp_page()
    payload = adapter.build("p-media-test", {"client": client, "page": page})
    assert payload["hero_image_url"] == custom_url


def test_content_stub_passes_template_style():
    """service_config_json['template_style'] yields payload['template_style']."""
    adapter = StubContentAdapter()
    client = _massage_client({"template_style": "spa"})
    page = _service_lp_page()
    payload = adapter.build("p-media-test", {"client": client, "page": page})
    assert payload.get("template_style") == "spa"


def test_content_stub_why_choose_us_no_duplicate_rating_no_raw_placeholder():
    """Why Choose Us has no duplicate '4.9★' entries and {price_anchor} is replaced."""
    adapter = StubContentAdapter()
    client = _massage_client()
    # Ensure client has no price_anchor to test fallback
    client.price_anchor = None
    page = _service_lp_page()
    payload = adapter.build("p-media-test", {"client": client, "page": page})
    sections = payload.get("sections", [])
    testimonials_section = next((s for s in sections if s.get("type") == "testimonials"), None)
    assert testimonials_section is not None
    items = testimonials_section.get("items", [])
    assert len(items) >= 1
    # No literal placeholder
    for item in items:
        assert "{price_anchor}" not in str(item), f"Raw placeholder in: {item}"
    # No duplicate rating lines (template has "4.9★...from verified"; focus_proof must not add "4.9★ average rating")
    rating_lines = [i for i in items if "4.9" in str(i) and "★" in str(i)]
    assert len(rating_lines) <= 1, f"Duplicate rating entries: {rating_lines}"


def test_content_stub_faq_qa_when_template_has_default_faq_qa():
    """Massage template has default_faq_qa; payload sections contain faq with Q&A pairs."""
    adapter = StubContentAdapter()
    client = _massage_client()
    page = _service_lp_page()
    payload = adapter.build("p-media-test", {"client": client, "page": page})
    sections = payload.get("sections", [])
    faq_section = next((s for s in sections if s.get("type") == "faq"), None)
    assert faq_section is not None, "sections should include faq"
    items = faq_section.get("items", [])
    assert len(items) >= 1, "faq items should not be empty"
    first = items[0]
    assert isinstance(first, dict), "faq items should be dicts with q and a"
    assert "q" in first, "faq item must have q key"
    assert "a" in first, "faq item must have a key"
    assert first["q"], "question should be non-empty"
    assert first["a"], "answer should be non-empty (template default_faq_qa provides both)"


def test_content_stub_includes_reviews_section_when_present():
    """service_config_json.reviews with 1+ item produces payload with reviews section."""
    adapter = StubContentAdapter()
    reviews = [
        {"quote": "Excellent service, highly recommend!", "author_name": "Jane D.", "rating": 5, "source": "google"},
    ]
    client = _massage_client({"reviews": reviews})
    page = _service_lp_page()
    payload = adapter.build("p-media-test", {"client": client, "page": page})
    sections = payload.get("sections", [])
    reviews_section = next((s for s in sections if s.get("type") == "reviews"), None)
    assert reviews_section is not None, "sections should include reviews when present"
    items = reviews_section.get("items", [])
    assert len(items) == 1
    assert items[0]["quote"] == "Excellent service, highly recommend!"
    assert items[0]["author_name"] == "Jane D."
    assert items[0]["rating"] == 5


def test_content_stub_no_starting_from_duplicate():
    """Why Choose Us / testimonials have no 'Starting from Starting from' duplication."""
    adapter = StubContentAdapter()
    client = _massage_client()
    page = _service_lp_page()
    payload = adapter.build("p-media-test", {"client": client, "page": page})
    sections = payload.get("sections", [])
    testimonials_section = next((s for s in sections if s.get("type") == "testimonials"), None)
    assert testimonials_section is not None
    for item in testimonials_section.get("items", []):
        assert "Starting from Starting from" not in str(item), f"Duplicate 'Starting from' in: {item}"


def test_content_stub_faq_hours_replaced_when_client_has_none():
    """FAQ hours placeholder uses template default when client.hours is empty."""
    adapter = StubContentAdapter()
    client = _massage_client()
    client.hours = None  # Simulate legacy client without hours
    page = _service_lp_page()
    payload = adapter.build("p-media-test", {"client": client, "page": page})
    sections = payload.get("sections", [])
    faq_section = next((s for s in sections if s.get("type") == "faq"), None)
    assert faq_section is not None
    hours_item = next((i for i in faq_section.get("items", []) if "operating hours" in str(i.get("q", "")).lower()), None)
    assert hours_item is not None
    assert "{hours}" not in hours_item.get("a", ""), "FAQ answer should have {hours} replaced with template default"


def test_content_stub_omits_reviews_section_when_empty():
    """reviews: [] or absent means no reviews section in payload."""
    adapter = StubContentAdapter()
    client = _massage_client({"reviews": []})
    page = _service_lp_page()
    payload = adapter.build("p-media-test", {"client": client, "page": page})
    sections = payload.get("sections", [])
    reviews_section = next((s for s in sections if s.get("type") == "reviews"), None)
    assert reviews_section is None, "should omit reviews section when empty"


def test_content_stub_no_media_when_template_empty():
    """Plumber (no media in template) returns hero_image_url None and gallery_images []."""
    adapter = StubContentAdapter()
    client = Client(
        client_id="media-test-plumber",
        client_name="Quick Plumber",
        trade=Trade.plumber,
        geo_country="AU",
        geo_city="Sydney",
        service_area=["Sydney"],
        primary_phone="+61-400-000-000",
        lead_email="test@example.com",
    )
    client = apply_trade_template_to_client(client)
    client.service_config_json = generate_default_service_config(client)
    page = Page(
        page_id="p-plumber",
        client_id="media-test-plumber",
        template_id="trade_lp",
        template_version="1.0",
        page_slug="quick-plumber",
        page_url="https://example.com/quick-plumber",
        page_status="draft",
        content_version=1,
    )
    payload = adapter.build("p-plumber", {"client": client, "page": page})
    assert payload.get("hero_image_url") is None
    assert payload.get("gallery_images") == []
