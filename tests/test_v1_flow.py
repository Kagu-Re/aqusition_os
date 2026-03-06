import os
import tempfile

from ae import db as dbmod
from ae.models import Client, Template, Page
from ae.enums import Trade, TemplateStatus, PageStatus, EventName, WorkType, Priority
from ae import repo, service

def test_publish_readiness_requires_events():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "acq.db")
        dbmod.init_db(db_path)

        repo.upsert_template(db_path, Template(
            template_id="trade_lp",
            template_name="Trades LP",
            template_version="1.0.0",
            cms_schema_version="1.0",
            compatible_events_version="1.0",
            status=TemplateStatus.active,
        ))

        repo.upsert_client(db_path, Client(
            client_id="demo1",
            client_name="Demo Plumbing",
            trade=Trade.plumber,
            geo_city="brisbane",
            service_area=["Brisbane North"],
            primary_phone="+61-400-000-000",
            lead_email="leads@example.com",
        ))

        repo.upsert_page(db_path, Page(
            page_id="p1",
            client_id="demo1",
            template_id="trade_lp",
            template_version="1.0.0",
            page_slug="demo-plumbing-v1",
            page_url="https://yourdomain.com/au/plumber-brisbane/demo-plumbing-v1",
            page_status=PageStatus.draft,
            content_version=1,
        ))

        ok, errors = service.validate_page(db_path, "p1")
        assert ok is False
        assert any("Tracking not validated" in e for e in errors)

def test_publish_after_events():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "acq.db")
        dbmod.init_db(db_path)

        repo.upsert_template(db_path, Template(
            template_id="trade_lp",
            template_name="Trades LP",
            template_version="1.0.0",
            cms_schema_version="1.0",
            compatible_events_version="1.0",
            status=TemplateStatus.active,
        ))

        repo.upsert_client(db_path, Client(
            client_id="demo1",
            client_name="Demo Plumbing",
            trade=Trade.plumber,
            geo_city="brisbane",
            service_area=["Brisbane North"],
            primary_phone="+61-400-000-000",
            lead_email="leads@example.com",
        ))

        repo.upsert_page(db_path, Page(
            page_id="p1",
            client_id="demo1",
            template_id="trade_lp",
            template_version="1.0.0",
            page_slug="demo-plumbing-v1",
            page_url="https://yourdomain.com/au/plumber-brisbane/demo-plumbing-v1",
            page_status=PageStatus.draft,
            content_version=1,
        ))

        # record synthetic validation events
        service.record_event(db_path, "p1", EventName.call_click, params={"cta_location":"hero"})
        service.record_event(db_path, "p1", EventName.quote_submit, params={"service_type":"blocked_drains"})
        service.record_event(db_path, "p1", EventName.thank_you_view, params={})

        ok, errors = service.validate_page(db_path, "p1")
        assert ok is True
        assert errors == []

        published, errs = service.publish_page(db_path, "p1", notes="v1 publish")
        assert published is True
        assert errs == []

        page = repo.get_page(db_path, "p1")
        assert page.page_status.value == "live"

def test_queue_enqueue_and_list():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "acq.db")
        dbmod.init_db(db_path)

        item = service.enqueue_work(db_path, WorkType.report, "demo1", None, Priority.normal, "Weekly report generated")
        items = repo.list_work(db_path)
        assert len(items) == 1
        assert items[0].work_item_id == item.work_item_id
