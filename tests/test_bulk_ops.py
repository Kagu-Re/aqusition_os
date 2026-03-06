import os
import tempfile

from ae import db as dbmod
from ae.models import Client, Template, Page, BulkOp
from ae.enums import Trade, TemplateStatus, PageStatus, EventName
from ae import repo, service

def _seed(db_path: str):
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
    service.record_event(db_path, "p1", EventName.call_click, params={})
    service.record_event(db_path, "p1", EventName.quote_submit, params={})
    service.record_event(db_path, "p1", EventName.thank_you_view, params={})

def test_bulk_publish_dry_run():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "acq.db")
        dbmod.init_db(db_path)
        _seed(db_path)

        op = BulkOp(
            bulk_id="bulk_test_1",
            action="publish",
            mode="dry_run",
            selector_json={"page_ids": ["p1"]},
            notes="batch",
        )
        repo.insert_bulk_op(db_path, op)

        res = service.run_bulk_op(db_path, "bulk_test_1")
        assert res["action"] == "publish"
        assert res["mode"] == "dry_run"
        assert res["items"][0]["would_publish"] is True
