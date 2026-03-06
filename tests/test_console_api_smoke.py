import os
from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod, repo
from ae.models import Client, Template, Page
from ae.enums import Trade, TemplateStatus, PageStatus


def _seed(db_path: str):
    dbmod.init_db(db_path)
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


def test_health_no_secret():
    os.environ.pop("AE_CONSOLE_SECRET", None)
    c = TestClient(app)
    r = c.get("/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_health_with_secret_requires_header(tmp_path):
    os.environ["AE_CONSOLE_SECRET"] = "s"
    c = TestClient(app)
    r = c.get("/api/health")
    assert r.status_code == 401
    r2 = c.get("/api/health", headers={"X-AE-SECRET": "s"})
    assert r2.status_code == 200
    assert r2.json()["ok"] is True


def test_pages_list_smoke(tmp_path):
    os.environ.pop("AE_CONSOLE_SECRET", None)
    db_path = str(tmp_path / "acq.db")
    _seed(db_path)
    c = TestClient(app)
    r = c.get("/api/pages", params={"db": db_path, "client_id": "c1"})
    assert r.status_code == 200
    j = r.json()
    assert j["count"] == 1
    assert j["items"][0]["page_id"] == "p1"
