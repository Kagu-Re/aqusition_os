import os
import tempfile
import csv
import json

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

def test_alias_registry_adds_custom_header_for_google_spend():
    with tempfile.TemporaryDirectory() as td:
        cwd=os.getcwd()
        os.chdir(td)
        try:
            # write custom alias file into expected ops path
            os.makedirs("ops", exist_ok=True)
            aliases = {
                "google": {
                    "timestamp": ["day"],
                    "impressions": ["impressions"],
                    "clicks": ["clicks"],
                    "spend": ["cost (usd)"],  # custom header
                    "revenue": ["conversion value"],
                }
            }
            with open("ops/ad_platform_aliases.json","w",encoding="utf-8") as f:
                json.dump(aliases,f)

            db_path=os.path.join(td,"acq.db")
            dbmod.init_db(db_path)
            _seed(db_path)

            csv_path=os.path.join(td,"google.csv")
            with open(csv_path,"w",newline="",encoding="utf-8") as f:
                wtr=csv.DictWriter(f, fieldnames=["Day","Impressions","Clicks","Cost (USD)","Conversion value"])
                wtr.writeheader()
                wtr.writerow({"Day":"2026-01-01","Impressions":"100","Clicks":"10","Cost (USD)":"20","Conversion value":"0"})

            rep=service.import_google_ads_export_csv(db_path, csv_path=csv_path, default_page_id="p1")
            assert rep["counters"]["inserted"] == 1

            k=service.kpi_report(db_path, "p1")["kpis"]
            assert k["spend"] == 20.0
        finally:
            os.chdir(cwd)
