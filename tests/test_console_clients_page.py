import os
from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod, repo
from ae.models import Client
from ae.enums import Trade


def test_console_clients_page_renders(tmp_path):
    db_path = str(tmp_path / "ae.db")
    dbmod.init_db(db_path)
    repo.upsert_client(db_path, Client(
        client_id="c1",
        client_name="Client One",
        trade=Trade.plumber,
        geo_country="TH",
        geo_city="chiang mai",
        service_area=["chiang mai"],
        primary_phone="+66-400-000-001",
        lead_email="leads@example.com",
    ))

    os.environ["AE_CONSOLE_SECRET"] = "s"
    c = TestClient(app)
    r = c.get("/console/clients", params={"db_path": db_path}, headers={"X-AE-SECRET": "s"})
    assert r.status_code == 200
    assert "Clients" in r.text
    assert "Client One" in r.text
