import os
import tempfile

from ae import db as dbmod
from ae.models import Client, Template, Page
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
        service_area=["Brisbane CBD"],
        primary_phone="+61-400-000-000",
        lead_email="leads@example.com",
    ))
    repo.upsert_page(db_path, Page(
        page_id="p1",
        client_id="demo1",
        template_id="trade_lp",
        template_version="1.0.0",
        page_slug="demo-1",
        page_url="https://example.com/1",
        page_status=PageStatus.draft,
        content_version=1,
    ))
    service.record_event(db_path, "p1", EventName.call_click, params={})
    service.record_event(db_path, "p1", EventName.quote_submit, params={})
    service.record_event(db_path, "p1", EventName.thank_you_view, params={})

def test_webflow_stub_publisher_writes_payload():
    with tempfile.TemporaryDirectory() as td:
        cwd=os.getcwd()
        os.chdir(td)
        try:
            db_path=os.path.join(td,"acq.db")
            dbmod.init_db(db_path)
            _seed(db_path)

            ok, errs = service.publish_page(
                db_path,
                "p1",
                notes="test webflow stub",
                adapter_config_override={"publisher": "webflow_stub", "webflow_out_dir": "exports/webflow_payloads"},
            )
            assert ok, errs
            out_path = os.path.join(td, "exports", "webflow_payloads", "p1.webflow.json")
            assert os.path.exists(out_path)
        finally:
            os.chdir(cwd)
