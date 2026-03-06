import os
import tempfile
import gc

from ae import db as dbmod
from ae.models import Client, Template, Page
from ae.enums import Trade, TemplateStatus, PageStatus, EventName
from ae import repo, service
from tests.test_helpers import force_close_db_connections

def _seed(db_path: str, n: int = 3):
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
    for i in range(1, n+1):
        pid = f"p{i}"
        repo.upsert_page(db_path, Page(
            page_id=pid,
            client_id="demo1",
            template_id="trade_lp",
            template_version="1.0.0",
            page_slug=f"demo-{i}",
            page_url=f"https://example.com/{i}",
            page_status=PageStatus.draft,
            content_version=1,
        ))
        # minimal events
        service.record_event(db_path, pid, EventName.call_click, params={})
        service.record_event(db_path, pid, EventName.quote_submit, params={})
        service.record_event(db_path, pid, EventName.thank_you_view, params={})

def test_bulk_publish_dry_run_counts():
    with tempfile.TemporaryDirectory() as td:
        cwd = os.getcwd()
        os.chdir(td)
        try:
            db_path = os.path.join(td, "acq.db")
            dbmod.init_db(db_path)
            _seed(db_path, n=2)
            op = service.run_bulk_publish(db_path, page_status="draft", limit=10, mode="dry_run")
            assert op.status == "done"
            c = op.result_json["counters"]
            assert c["total"] == 2
            # either would_publish or failed, but should not mark published in dry run
            assert c.get("published", 0) == 0
        finally:
            # Force close connections before cleanup (Windows file locking fix)
            db_path = os.path.join(td, "acq.db")
            if os.path.exists(db_path):
                force_close_db_connections(db_path)
            gc.collect()
            os.chdir(cwd)

def test_bulk_publish_execute_publishes_and_is_idempotent():
    with tempfile.TemporaryDirectory() as td:
        cwd = os.getcwd()
        os.chdir(td)
        try:
            db_path = os.path.join(td, "acq.db")
            dbmod.init_db(db_path)
            _seed(db_path, n=2)

            op1 = service.run_bulk_publish(
                db_path,
                page_status="draft",
                limit=10,
                mode="execute",
                adapter_config_override={"publisher": "tailwind_static", "static_out_dir": "exports/static_site"},
            )
            assert op1.status == "done"
            c1 = op1.result_json["counters"]
            assert c1["published"] == 2
            assert os.path.exists(os.path.join(td, "exports", "static_site", "p1", "index.html"))

            # second run should skip (already live)
            op2 = service.run_bulk_publish(
                db_path,
                page_ids=["p1","p2"],
                mode="execute",
                adapter_config_override={"publisher": "tailwind_static", "static_out_dir": "exports/static_site"},
            )
            c2 = op2.result_json["counters"]
            assert c2["skipped"] == 2
        finally:
            # Force close connections before cleanup (Windows file locking fix)
            db_path = os.path.join(td, "acq.db")
            if os.path.exists(db_path):
                force_close_db_connections(db_path)
            gc.collect()
            os.chdir(cwd)
