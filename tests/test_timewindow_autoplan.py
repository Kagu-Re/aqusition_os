import json
from datetime import datetime, timezone
from typer.testing import CliRunner

from ae.cli import app
from ae.timewindow import window_to_since_iso
from ae import db as dbmod
from ae.models import Client, Page, Template
from ae import repo


def test_window_to_since_iso():
    r = window_to_since_iso("7d", now=datetime(2026, 2, 2, tzinfo=timezone.utc))
    assert r.window == "7d"
    assert r.since_iso.startswith("2026-01-26")


def _seed(db_path: str):
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
    repo.upsert_page(db_path, Page(
        page_id="p1",
        client_id="c1",
        template_id="t1",
        template_version="1.0.0",
        page_slug="p-1",
        page_url="https://example.com/p-1",
        page_status="live",
        content_version=1,
        locale="en",
    ))

    runner = CliRunner()
    res = runner.invoke(app, ["ads-pull-stats", "--db", db_path, "--platform", "meta", "--client-id", "c1"])
    assert res.exit_code == 0, res.stdout


def test_autoplan_runs(tmp_path):
    db_path = str(tmp_path / "t.db")
    _seed(db_path)

    runner = CliRunner()
    res = runner.invoke(app, ["guardrails-autoplan", "--db", db_path, "--client-id", "c1", "--platform", "meta", "--window", "30d", "--fmt", "json"])
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    assert payload["summary"]["client_id"] == "c1"
    # No leads -> should include at least one plan (clicks_no_leads)
    assert len(payload.get("plans", [])) >= 1
