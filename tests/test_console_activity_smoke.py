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


def test_activity_endpoint_and_bulk_logging(tmp_path):
    os.environ.pop("AE_CONSOLE_SECRET", None)
    db_path = str(tmp_path / "acq.db")
    _seed(db_path)

    c = TestClient(app)

    # run a bulk validate (dry)
    payload = {
        "action": "validate",
        "db": db_path,
        "client_id": "c1",
        "execute": False,
        "limit": 50
    }
    r = c.post("/api/bulk/run", json=payload)
    assert r.status_code == 200

    # activity should include bulk_validate
    r2 = c.get("/api/activity", params={"db": db_path, "limit": 50})
    assert r2.status_code == 200
    j = r2.json()
    assert j["count"] >= 1
    assert any(it["action"] == "bulk_validate" for it in j["items"])

    # dry publish should include preview_dir + diff counters
    payload2 = {
        "action": "publish",
        "db": db_path,
        "client_id": "c1",
        "execute": False,
        "limit": 50
    }
    r3 = c.post("/api/bulk/run", json=payload2)
    assert r3.status_code == 200
    j3 = r3.json()
    assert "preview_dir" in j3.get("result_json", {})
    counters = j3["result_json"]["counters"]
    assert "changed" in counters and "unchanged" in counters

