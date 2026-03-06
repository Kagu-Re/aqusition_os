import json
from datetime import datetime, timezone
from typer.testing import CliRunner

from ae.cli import app
from ae import db as dbmod
from ae.models import Client, Page, Template, LeadIntake
from ae import repo


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
        page_slug="p1",
        page_url="https://example.com/p1",
        page_status="live",
        content_version=1,
        locale="en",
    ))
    # Pull ad stats (stub) into DB so we have clicks/spend
    runner = CliRunner()
    res = runner.invoke(app, ["ads-pull-stats", "--db", db_path, "--platform", "meta", "--client-id", "c1"])
    assert res.exit_code == 0, res.stdout

    # Insert zero leads (so clicks>0 leads==0 triggers CRIT)
    # Also insert one lead on another page-less case? skip.
    now = datetime.now(timezone.utc).isoformat()
    # We'll add 1 spam lead to confirm spam excluded
    repo.insert_lead(db_path, LeadIntake(
        ts=now, source="web", page_id="p1", client_id="c1",
        name="n", phone="", email="", message="m",
        utm_source="meta", utm_medium="cpc", utm_campaign="x", utm_term="", utm_content="",
        referrer="", user_agent="", ip_hint="",
        spam_score=1.0, is_spam=1, status="new",
        booking_status="none", booking_value=None, booking_currency=None, booking_ts=None,
        meta_json={},
    ))


def test_diagnostics_json(tmp_path):
    db_path = str(tmp_path / "t.db")
    _seed(db_path)

    runner = CliRunner()
    res = runner.invoke(app, ["diagnostics-client", "--db", db_path, "--client-id", "c1", "--platform", "meta"])
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)

    assert payload["summary"]["client_id"] == "c1"
    # Should contain CLICK_NO_LEADS as crit for p1
    codes = [i["code"] for i in payload["issues"]]
    assert "CLICKS_NO_LEADS" in codes


def test_diagnostics_markdown(tmp_path):
    db_path = str(tmp_path / "t.db")
    _seed(db_path)

    runner = CliRunner()
    res = runner.invoke(app, ["diagnostics-client", "--db", db_path, "--client-id", "c1", "--platform", "meta", "--fmt", "markdown"])
    assert res.exit_code == 0, res.stdout
    assert "| severity | code |" in res.stdout
