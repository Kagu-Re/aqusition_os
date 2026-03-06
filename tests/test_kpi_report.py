import json
from datetime import datetime, timezone
from typer.testing import CliRunner

from ae.cli import app
from ae import db as dbmod
from ae.models import Client, Page, Template, LeadIntake, EventRecord
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

    # Insert stub ad_stats via CLI to ensure wiring works
    runner = CliRunner()
    res = runner.invoke(app, ["ads-pull-stats", "--db", db_path, "--platform", "meta", "--client-id", "c1"])
    assert res.exit_code == 0, res.stdout

    # Leads: 3 on p1, 1 on p2
    now = datetime.now(timezone.utc).isoformat()
    for _ in range(3):
        repo.insert_lead(db_path, LeadIntake(
            ts=now, source="web", page_id="p1", client_id="c1",
            name="n", phone="", email="", message="m",
            utm_source="meta", utm_medium="cpc", utm_campaign="x", utm_term="", utm_content="",
            referrer="", user_agent="", ip_hint="",
            spam_score=0.0, is_spam=0, status="new",
            booking_status="none", booking_value=None, booking_currency=None, booking_ts=None,
            meta_json={},
        ))
    repo.insert_lead(db_path, LeadIntake(
        ts=now, source="web", page_id="p2", client_id="c1",
        name="n", phone="", email="", message="m",
        utm_source="meta", utm_medium="cpc", utm_campaign="x", utm_term="", utm_content="",
        referrer="", user_agent="", ip_hint="",
        spam_score=0.0, is_spam=0, status="new",
        booking_status="none", booking_value=None, booking_currency=None, booking_ts=None,
        meta_json={},
    ))

    # Booking events: 1 on p1
    repo.insert_event(db_path, EventRecord(
        event_id="e1",
        timestamp=datetime.now(timezone.utc),
        page_id="p1",
        event_name="thank_you_view",
        session_id="s1",
        visitor_id="v1",
        params_json={},
    ))


def test_kpi_report_json(tmp_path):
    db_path = str(tmp_path / "t.db")
    _seed(db_path)

    runner = CliRunner()
    res = runner.invoke(app, ["kpi-client-report", "--db", db_path, "--client-id", "c1", "--platform", "meta"])
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    assert payload["summary"]["client_id"] == "c1"
    assert payload["summary"]["pages"] == 2
    # totals
    assert payload["summary"]["totals"]["leads"] == 4
    assert payload["summary"]["totals"]["bookings"] == 1
    assert payload["summary"]["totals"]["spend"] > 0


def test_kpi_report_markdown(tmp_path):
    db_path = str(tmp_path / "t.db")
    _seed(db_path)

    runner = CliRunner()
    res = runner.invoke(app, ["kpi-client-report", "--db", db_path, "--client-id", "c1", "--platform", "meta", "--fmt", "markdown"])
    assert res.exit_code == 0, res.stdout
    assert "| page_id |" in res.stdout
    assert "p1" in res.stdout
