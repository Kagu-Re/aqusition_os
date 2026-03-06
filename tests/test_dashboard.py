import json
from datetime import datetime, timezone
from typer.testing import CliRunner

from ae.cli import app
from ae import db as dbmod
from ae.models import Client, Page, Template, LeadIntake, EventRecord
from ae import repo


def _seed(db_path: str):
    dbmod.init_db(db_path)

    # Templates
    repo.upsert_template(db_path, Template(
        template_id="t1",
        template_name="Base",
        template_version="1.0.0",
        cms_schema_version="1",
        compatible_events_version="1",
        status="active",
    ))

    # Client FAIL (clicks but no leads)
    repo.upsert_client(db_path, Client(
        client_id="c_fail",
        client_name="Fail Client",
        trade="plumber",
        geo_country="TH",
        geo_city="chiang mai",
        service_area=["chiang mai"],
        primary_phone="+66000000000",
        lead_email="lead@example.com",
        status="live",
        license_badges=[],
    ))
    repo.upsert_page(db_path, Page(
        page_id="p_fail",
        client_id="c_fail",
        template_id="t1",
        template_version="1.0.0",
        page_slug="p-fail",
        page_url="https://example.com/p-fail",
        page_status="live",
        content_version=1,
        locale="en",
    ))

    # Client PASS-ish (has leads + thank_you_view)
    repo.upsert_client(db_path, Client(
        client_id="c_ok",
        client_name="Ok Client",
        trade="hvac",
        geo_country="TH",
        geo_city="chiang mai",
        service_area=["chiang mai"],
        primary_phone="+66000000000",
        lead_email="lead@example.com",
        status="live",
        license_badges=[],
    ))
    repo.upsert_page(db_path, Page(
        page_id="p_ok",
        client_id="c_ok",
        template_id="t1",
        template_version="1.0.0",
        page_slug="p-ok",
        page_url="https://example.com/p-ok",
        page_status="live",
        content_version=1,
        locale="en",
    ))

    runner = CliRunner()
    # Add stub ad_stats for both clients
    res1 = runner.invoke(app, ["ads-pull-stats", "--db", db_path, "--platform", "meta", "--client-id", "c_fail"])
    assert res1.exit_code == 0, res1.stdout
    res2 = runner.invoke(app, ["ads-pull-stats", "--db", db_path, "--platform", "meta", "--client-id", "c_ok"])
    assert res2.exit_code == 0, res2.stdout

    # Insert lead + booking proxy for ok client
    now = datetime.now(timezone.utc).isoformat()
    repo.insert_lead(db_path, LeadIntake(
        ts=now, source="web", page_id="p_ok", client_id="c_ok",
        name="n", phone="", email="", message="m",
        utm_source="meta", utm_medium="cpc", utm_campaign="x", utm_term="", utm_content="",
        referrer="", user_agent="", ip_hint="",
        spam_score=0.0, is_spam=0, status="new",
        booking_status="none", booking_value=None, booking_currency=None, booking_ts=None,
        meta_json={},
    ))
    repo.insert_event(db_path, EventRecord(
        event_id="e_ok",
        timestamp=datetime.now(timezone.utc),
        page_id="p_ok",
        event_name="thank_you_view",
        session_id="s1",
        visitor_id="v1",
        params_json={},
    ))


def test_guardrails_dashboard_markdown(tmp_path):
    db_path = str(tmp_path / "t.db")
    _seed(db_path)

    runner = CliRunner()
    res = runner.invoke(app, ["guardrails-dashboard", "--db", db_path, "--platform", "meta", "--fmt", "markdown"])
    assert res.exit_code == 0, res.stdout
    assert "Guardrails dashboard" in res.stdout
    assert "c_fail" in res.stdout
    assert "c_ok" in res.stdout


def test_guardrails_dashboard_json(tmp_path):
    db_path = str(tmp_path / "t.db")
    _seed(db_path)

    runner = CliRunner()
    res = runner.invoke(app, ["guardrails-dashboard", "--db", db_path, "--platform", "meta", "--fmt", "json"])
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    assert payload["summary"]["clients_evaluated"] == 2
    statuses = {r["client_id"]: r["status"] for r in payload["rows"]}
    assert statuses["c_fail"] == "FAIL"
