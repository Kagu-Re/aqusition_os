import os
import tempfile
import gc

from ae import db as dbmod
from ae.models import Client, Template, Page
from ae.enums import Trade, TemplateStatus, PageStatus
from ae import repo, service
from tests.test_helpers import force_close_db_connections

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
        client_id="c1",
        client_name="Client One",
        trade=Trade.plumber,
        geo_country="au",
        geo_city="brisbane",
        service_area=["Brisbane CBD"],
        primary_phone="+61-400-000-001",
        lead_email="leads1@example.com",
    ))
    repo.upsert_client(db_path, Client(
        client_id="c2",
        client_name="Client Two",
        trade=Trade.plumber,
        geo_country="au",
        geo_city="sydney",
        service_area=["Sydney CBD"],
        primary_phone="+61-400-000-002",
        lead_email="leads2@example.com",
    ))
    # pages
    repo.upsert_page(db_path, Page(
        page_id="p1",
        client_id="c1",
        template_id="trade_lp",
        template_version="1.0.0",
        page_slug="p1",
        page_url="https://example.com/p1",
        page_status=PageStatus.draft,
        content_version=1,
    ))
    repo.upsert_page(db_path, Page(
        page_id="p2",
        client_id="c1",
        template_id="trade_lp",
        template_version="1.0.0",
        page_slug="p2",
        page_url="https://example.com/p2",
        page_status=PageStatus.draft,
        content_version=1,
    ))
    repo.upsert_page(db_path, Page(
        page_id="p3",
        client_id="c2",
        template_id="trade_lp",
        template_version="1.0.0",
        page_slug="p3",
        page_url="https://example.com/p3",
        page_status=PageStatus.draft,
        content_version=1,
    ))

def test_bulk_validate_selector_geo_city_counts_total():
    with tempfile.TemporaryDirectory() as td:
        db_path=os.path.join(td,"acq.db")
        try:
            dbmod.init_db(db_path)
            _seed(db_path)

            op=service.run_bulk_validate(db_path, geo_city="brisbane", limit=10)
            assert op.result_json["counters"]["total"] == 2
        finally:
            # Force close connections before cleanup (Windows file locking fix)
            if os.path.exists(db_path):
                force_close_db_connections(db_path)
            gc.collect()

def test_bulk_pause_execute_by_client_id_changes_status():
    with tempfile.TemporaryDirectory() as td:
        db_path=os.path.join(td,"acq.db")
        try:
            dbmod.init_db(db_path)
            _seed(db_path)

            op=service.run_bulk_pause(db_path, client_id="c1", mode="execute", limit=10, notes="pause batch")
            assert op.result_json["counters"]["paused"] == 2
            assert repo.get_page(db_path, "p1").page_status == PageStatus.paused
            assert repo.get_page(db_path, "p2").page_status == PageStatus.paused
            assert repo.get_page(db_path, "p3").page_status == PageStatus.draft
        finally:
            # Force close connections before cleanup (Windows file locking fix)
            if os.path.exists(db_path):
                force_close_db_connections(db_path)
            gc.collect()
