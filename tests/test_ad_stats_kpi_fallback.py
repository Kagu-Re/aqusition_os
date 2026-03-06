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
    # 2 leads events
    service.record_event(db_path, "p1", EventName.call_click, params={})
    service.record_event(db_path, "p1", EventName.quote_submit, params={})

def test_kpi_report_falls_back_to_ad_stats():
    with tempfile.TemporaryDirectory() as td:
        cwd=os.getcwd()
        os.chdir(td)
        try:
            db_path=os.path.join(td,"acq.db")
            dbmod.init_db(db_path)
            _seed(db_path)

            # record ad stats
            service.record_ad_stat(db_path, "p1", platform="meta", impressions=1000, clicks=50, spend=100.0, revenue=0.0)

            rep = service.kpi_report(db_path, "p1")  # no placeholders
            k = rep["kpis"]
            assert k["impressions"] == 1000
            assert k["clicks"] == 50
            assert abs(k["ctr"] - 0.05) < 1e-9
            assert abs(k["cpc"] - 2.0) < 1e-9
        finally:
            os.chdir(cwd)
