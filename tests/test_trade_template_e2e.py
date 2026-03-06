"""End-to-end test: massage client -> content build -> publish with hero and gallery."""

import os
import tempfile

from ae import db as dbmod
from ae.models import Client, Template, Page
from ae.enums import Trade, BusinessModel, TemplateStatus, PageStatus, EventName
from ae import repo, service
from ae.adapters.registry import resolve_adapters


def _seed_massage_e2e(db_path: str) -> None:
    """Seed DB with service_lp template, massage client, and page."""
    repo.upsert_template(db_path, Template(
        template_id="service_lp",
        template_name="Service Landing Page",
        template_version="1.0.0",
        cms_schema_version="1.0",
        compatible_events_version="1.0",
        status=TemplateStatus.active,
    ))
    repo.upsert_client(db_path, Client(
        client_id="e2e-massage",
        client_name="Serenity Massage",
        trade=Trade.massage,
        business_model=BusinessModel.fixed_price,
        geo_country="TH",
        geo_city="Bangkok",
        service_area=["Bangkok"],
        primary_phone="+66-80-000-0000",
        lead_email="e2e@example.com",
    ), apply_defaults=True)
    repo.upsert_page(db_path, Page(
        page_id="p-e2e-massage",
        client_id="e2e-massage",
        template_id="service_lp",
        template_version="1.0.0",
        page_slug="serenity-massage",
        page_url="https://example.com/serenity-massage",
        page_status=PageStatus.draft,
        content_version=1,
    ))
    for evt in [EventName.call_click, EventName.quote_submit, EventName.thank_you_view]:
        service.record_event(db_path, "p-e2e-massage", evt, params={})


def test_trade_template_e2e_build_and_publish(tmp_path):
    """Full flow: massage client -> build content -> publish -> verify hero and gallery in HTML."""
    db_path = str(tmp_path / "e2e.db")
    out_dir = str(tmp_path / "exports")
    dbmod.init_db(db_path)
    _seed_massage_e2e(db_path)

    adapters = resolve_adapters(repo, {"static_out_dir": out_dir})
    page = repo.get_page(db_path, "p-e2e-massage")
    client = repo.get_client(db_path, "e2e-massage")
    context = {"page": page, "client": client, "db_path": db_path}

    payload = adapters.content.build("p-e2e-massage", context)
    assert "hero_image_url" in payload
    assert payload["hero_image_url"] is not None
    assert payload["hero_image_url"].startswith("http")
    assert "gallery_images" in payload
    assert len(payload["gallery_images"]) >= 3

    result = adapters.publisher.publish("p-e2e-massage", payload, context)
    assert result.ok is True
    assert result.artifact_path

    html_path = os.path.join(out_dir, "p-e2e-massage", "index.html")
    assert os.path.exists(html_path)
    html = open(html_path, encoding="utf-8").read()
    # URL may be HTML-escaped (& -> &amp;)
    hero_in_html = payload["hero_image_url"] in html or payload["hero_image_url"].replace("&", "&amp;") in html
    assert hero_in_html, "Hero image URL should appear in HTML"
    assert "Gallery" in html
    assert html.count("<img") >= 4  # 1 hero + 3+ gallery
