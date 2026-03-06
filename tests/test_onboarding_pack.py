import json
from pathlib import Path

from typer.testing import CliRunner

from ae.cli import app
from ae import db as dbmod
from ae.models import Client
from ae import repo


def test_generate_onboarding_pack_cli(tmp_path):
    db_path = tmp_path / "t.db"
    dbmod.init_db(str(db_path))

    c = Client(
        client_id="plumber-cm",
        client_name="Plumber CM",
        trade="plumber",
        geo_country="TH",
        geo_city="chiang mai",
        service_area=["chiang mai"],
        primary_phone="+66000000000",
        lead_email="lead@example.com",
        notes_internal="Emergency leak repair",
    )
    repo.upsert_client(str(db_path), c)

    out_root = tmp_path / "clients_out"
    runner = CliRunner()
    result = runner.invoke(app, ["generate-onboarding", "--db", str(db_path), "--client-id", "plumber-cm", "--out-root", str(out_root)])
    assert result.exit_code == 0, result.stdout

    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["client_id"] == "plumber-cm"
    files = payload["files"]
    assert set(files.keys()) == {"utm_policy.md", "event_map.md", "naming_convention.md", "first_7_days.md"}

    for name, p in files.items():
        path = Path(p)
        assert path.exists()
        txt = path.read_text(encoding="utf-8")
        assert "plumber-cm" in txt
