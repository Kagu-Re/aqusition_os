import json
from typer.testing import CliRunner

from ae.ads import get_ads_adapter
from ae.ads.base import AssetSpec
from ae.cli import app


def test_ads_stubs_contract():
    meta = get_ads_adapter("meta")
    google = get_ads_adapter("google")

    s = meta.pull_spend(client_id="c1", date_from="2026-01-01", date_to="2026-01-07")
    r = meta.pull_results(client_id="c1", date_from="2026-01-01", date_to="2026-01-07")
    assert s.spend > 0
    assert s.clicks > 0
    assert r.leads >= 0

    ack = meta.push_assets(client_id="c1", assets=[AssetSpec(asset_id="a1", headline="h", primary_text="t")])
    assert ack["ok"] is True
    assert ack["created"][0]["platform_asset_id"].startswith("meta_c1_")

    s2 = google.pull_spend(client_id="c1", date_from="2026-01-01", date_to="2026-01-07")
    r2 = google.pull_results(client_id="c1", date_from="2026-01-01", date_to="2026-01-07")
    assert s2.spend > 0
    assert r2.bookings >= 0


def test_cli_ads_simulate():
    runner = CliRunner()
    result = runner.invoke(app, ["ads-simulate", "--platform", "meta", "--client-id", "plumber-cm"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["platform"] == "meta"
    assert "spend" in payload and "results" in payload
