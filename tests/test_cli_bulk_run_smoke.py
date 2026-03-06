import os
import subprocess
import sys
import tempfile

from ae import db as dbmod
from ae.models import Client, Template, Page
from ae.enums import Trade, TemplateStatus, PageStatus
from ae import repo

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

def test_cli_bulk_run_validate_smoke():
    with tempfile.TemporaryDirectory() as td:
        db_path=os.path.join(td,"acq.db")
        dbmod.init_db(db_path)
        _seed(db_path)

        env=dict(os.environ)
        # ensure module resolution
        repo_root=os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        env["PYTHONPATH"]=os.path.join(repo_root, "src") + (os.pathsep + env.get("PYTHONPATH") if env.get("PYTHONPATH") else "")

        p=subprocess.run(
            [sys.executable, "-m", "ae.cli", "bulk-run", "--action", "validate", "--db", db_path, "--client-id", "c1"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert p.returncode == 0
        assert "bulk_id=" in p.stdout
