import os
import tempfile
import subprocess
import sys

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

def test_service_publish_accepts_adapter_override_without_env():
    with tempfile.TemporaryDirectory() as td:
        cwd = os.getcwd()
        os.chdir(td)
        try:
            db_path = os.path.join(td, "acq.db")
            dbmod.init_db(db_path)
            _seed(db_path)
            ok, errs = service.publish_page(
                db_path,
                "p1",
                notes="test",
                adapter_config_override={"publisher": "tailwind_static", "static_out_dir": "exports/static_site"},
            )
            assert ok is True
            assert errs == []
            assert os.path.exists(os.path.join(td, "exports", "static_site", "p1", "index.html"))
        finally:
            os.chdir(cwd)

def test_cli_publish_page_override_args():
    with tempfile.TemporaryDirectory() as td:
        cwd = os.getcwd()
        os.chdir(td)
        try:
            db_path = os.path.join(td, "acq.db")
            dbmod.init_db(db_path)
            _seed(db_path)
            env = os.environ.copy()
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            env['PYTHONPATH'] = os.path.join(repo_root, 'src') + (os.pathsep + env.get('PYTHONPATH','') if env.get('PYTHONPATH') else '')
            env.pop("AE_PUBLISHER_ADAPTER", None)
            env.pop("AE_STATIC_OUT_DIR", None)
            p = subprocess.run(
                [sys.executable, "-m", "ae.cli", "publish-page", "--db", db_path, "--page-id", "p1",
                 "--publisher-adapter", "tailwind_static", "--static-out-dir", "exports/static_site"],
                capture_output=True,
                text=True,
                env=env,
            )
            assert p.returncode == 0, p.stdout + p.stderr
            assert os.path.exists(os.path.join(td, "exports", "static_site", "p1", "index.html"))
        finally:
            os.chdir(cwd)
