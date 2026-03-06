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
    # 3 call clicks, 1 quote, 1 thank you => leads=4 bookings=1
    for _ in range(3):
        service.record_event(db_path, "p1", EventName.call_click, params={})
    service.record_event(db_path, "p1", EventName.quote_submit, params={})
    service.record_event(db_path, "p1", EventName.thank_you_view, params={})

def test_kpi_report_computes_rates_when_inputs_present():
    with tempfile.TemporaryDirectory() as td:
        cwd=os.getcwd()
        os.chdir(td)
        try:
            db_path=os.path.join(td,"acq.db")
            dbmod.init_db(db_path)
            _seed(db_path)
            rep = service.kpi_report(db_path, "p1", impressions=1000, clicks=100, spend=200.0, revenue=1000.0)
            k = rep["kpis"]
            assert k["leads"] == 4
            assert k["bookings"] == 1
            assert abs(k["ctr"] - 0.1) < 1e-9
            assert abs(k["lead_rate"] - 0.04) < 1e-9
            assert abs(k["lead_to_booking_rate"] - 0.25) < 1e-9
            assert abs(k["cpc"] - 2.0) < 1e-9
            assert abs(k["roas"] - 5.0) < 1e-9
        finally:
            os.chdir(cwd)

def test_kpi_report_nulls_when_inputs_missing():
    with tempfile.TemporaryDirectory() as td:
        cwd=os.getcwd()
        os.chdir(td)
        try:
            db_path=os.path.join(td,"acq.db")
            dbmod.init_db(db_path)
            _seed(db_path)
            rep = service.kpi_report(db_path, "p1")
            k = rep["kpis"]
            assert k["ctr"] is None
            assert k["cpc"] is None
        finally:
            os.chdir(cwd)
