import json
from typer.testing import CliRunner

from ae.cli import app
from ae import db as dbmod
from ae.models import Client, Page, Template
from ae import repo


def _seed_minimal(db_path: str):
    dbmod.init_db(db_path)
    repo.upsert_client(db_path, Client(
        client_id="c1",
        client_name="Client One",
        trade="plumber",
        geo_country="TH",
        geo_city="chiang mai",
        service_area=["chiang mai"],
        primary_phone="+66000000000",
        lead_email="lead@example.com",
        status="live",
        license_badges=[],
    ))
    repo.upsert_template(db_path, Template(
        template_id="t1",
        template_name="Base",
        template_version="1.0.0",
        cms_schema_version="1",
        compatible_events_version="1",
        status="active",
    ))
    # 2 pages to distribute
    repo.upsert_page(db_path, Page(
        page_id="p1",
        client_id="c1",
        template_id="t1",
        template_version="1.0.0",
        page_slug="p1",
        page_url="https://example.com/p1",
        page_status="live",
        content_version=1,
        locale="en",
    ))
    repo.upsert_page(db_path, Page(
        page_id="p2",
        client_id="c1",
        template_id="t1",
        template_version="1.0.0",
        page_slug="p2",
        page_url="https://example.com/p2",
        page_status="live",
        content_version=1,
        locale="en",
    ))


def test_ads_pull_stats_inserts_rows(tmp_path):
    db_path = str(tmp_path / "t.db")
    _seed_minimal(db_path)

    runner = CliRunner()
    res = runner.invoke(app, ["ads-pull-stats", "--db", db_path, "--platform", "meta", "--client-id", "c1"])
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    assert payload["ok"] is True
    assert payload["pages"] == 2
    assert len(payload["inserted"]) == 2

    s1 = repo.sum_ad_stats(db_path, page_id="p1", platform="meta")
    s2 = repo.sum_ad_stats(db_path, page_id="p2", platform="meta")
    assert s1["spend"] > 0
    assert s2["spend"] > 0
    # totals should roughly equal stub totals; rounding distributes integers
    total_spend = s1["spend"] + s2["spend"]
    assert 119.0 <= total_spend <= 121.0
