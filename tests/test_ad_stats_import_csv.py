import os
import tempfile
import csv

from ae import db as dbmod
from ae.models import Client, Template, Page
from ae.enums import Trade, TemplateStatus, PageStatus
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

def test_import_ad_stats_csv_inserts_rows():
    with tempfile.TemporaryDirectory() as td:
        cwd=os.getcwd()
        os.chdir(td)
        try:
            db_path=os.path.join(td,"acq.db")
            dbmod.init_db(db_path)
            _seed(db_path)

            csv_path=os.path.join(td,"ad_stats.csv")
            with open(csv_path,"w",newline="",encoding="utf-8") as f:
                wtr=csv.DictWriter(f, fieldnames=["page_id","platform","timestamp","impressions","clicks","spend","revenue"])
                wtr.writeheader()
                wtr.writerow({"page_id":"p1","platform":"meta","timestamp":"2026-01-01T00:00:00","impressions":"1000","clicks":"50","spend":"100","revenue":"0"})

            rep=service.import_ad_stats_csv(db_path, csv_path)
            assert rep["counters"]["inserted"] == 1

            k=service.kpi_report(db_path, "p1")["kpis"]
            assert k["impressions"] == 1000
            assert k["clicks"] == 50
        finally:
            os.chdir(cwd)
