import json
from pathlib import Path
from typer.testing import CliRunner

from ae.cli import app
from ae import db as dbmod
from ae.models import Client, Page, Template
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
        page_slug="p-1",
        page_url="https://example.com/p-1",
        page_status="live",
        content_version=1,
        locale="en",
    ))


def test_ops_run_creates_patch_and_promotes_work(tmp_path):
    db_path = str(tmp_path / "t.db")
    _seed(db_path)

    patchq = tmp_path / "PATCH_QUEUE.md"
    workq = tmp_path / "WORK_QUEUE.md"
    logp = tmp_path / "LOG_HORIZON.md"

    runner = CliRunner()
    # Pull stats so guardrails have data
    r0 = runner.invoke(app, ["ads-pull-stats", "--db", db_path, "--platform", "meta", "--client-id", "c1"])
    assert r0.exit_code == 0, r0.stdout

    r1 = runner.invoke(app, [
        "ops-run",
        "--db", db_path,
        "--client-id", "c1",
        "--platform", "meta",
        "--window", "30d",
        "--assignee", "rm",
        "--patch-queue-path", str(patchq),
        "--work-queue-path", str(workq),
        "--log-path", str(logp),
    ])
    assert r1.exit_code == 0, r1.stdout
    payload = json.loads(r1.stdout)
    assert payload["autoplan_patch_id"].startswith("AP-")
    assert len(payload["promoted_work_ids"]) == 1

    assert patchq.exists()
    assert workq.exists()
    assert logp.exists()
    assert payload["autoplan_patch_id"] in patchq.read_text(encoding="utf-8")
    wid = payload["promoted_work_ids"][0]
    assert wid in workq.read_text(encoding="utf-8")

    # Running again should create another patch (different id likely) but promotion should still add 1 row; can dedup only by work_id, so new patch creates new work.
    r2 = runner.invoke(app, [
        "ops-run",
        "--db", db_path,
        "--client-id", "c1",
        "--platform", "meta",
        "--window", "30d",
        "--assignee", "rm",
        "--patch-queue-path", str(patchq),
        "--work-queue-path", str(workq),
        "--log-path", str(logp),
    ])
    assert r2.exit_code == 0, r2.stdout
    payload2 = json.loads(r2.stdout)
    assert payload2["autoplan_patch_id"] in patchq.read_text(encoding="utf-8")
