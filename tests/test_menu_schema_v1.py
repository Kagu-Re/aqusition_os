import os
from fastapi.testclient import TestClient

from ae.console_app import app
from ae import db as dbmod, repo
from ae.models import Client
from ae.enums import Trade


def _seed(db_path: str):
    dbmod.init_db(db_path)
    repo.upsert_client(db_path, Client(
        client_id="c1",
        client_name="Client One",
        trade=Trade.plumber,
        geo_country="th",
        geo_city="chiang_mai",
        service_area=["CM"],
        primary_phone="000",
        lead_email="a@example.com",
        status="live",
        hours=None,
        license_badges=[],
        price_anchor=None,
        brand_theme=None,
        notes_internal=None,
    ))


def test_menu_crud_smoke(tmp_path):
    db_path = str(tmp_path / "t.db")
    _seed(db_path)
    os.environ.pop("AE_CONSOLE_SECRET", None)
    os.environ.pop("AE_CONSOLE_SECRET", None)
    client = TestClient(app)

    r = client.post("/api/menus?db=" + db_path, json={
        "menu_id": "m1",
        "client_id": "c1",
        "name": "Main Menu",
        "language": "en",
        "currency": "THB",
        "status": "draft",
        "meta": {"source": "test"}
    })
    assert r.status_code == 200
    r2 = client.get("/api/menus/m1?db=" + db_path)
    assert r2.status_code == 200
    body = r2.json()
    assert body["menu"]["menu_id"] == "m1"

    # add section + item
    rs = client.post("/api/menus/m1/sections?db=" + db_path, json={"section_id": "s1", "title": "Drinks", "sort_order": 1})
    assert rs.status_code == 200
    ri = client.post("/api/menus/m1/items?db=" + db_path, json={"item_id": "i1", "section_id": "s1", "title": "Tea", "price": 60, "currency": "THB", "is_available": True, "sort_order": 1, "meta": {}})
    assert ri.status_code == 200

    r3 = client.get("/api/menus/m1?db=" + db_path)
    assert r3.status_code == 200
    b3 = r3.json()
    assert len(b3["sections"]) == 1
    assert len(b3["items"]) == 1


def test_list_menus_filter(tmp_path):
    db_path = str(tmp_path / "t.db")
    _seed(db_path)
    os.environ.pop("AE_CONSOLE_SECRET", None)
    client = TestClient(app)
    client.post("/api/menus?db=" + db_path, json={"menu_id": "m1", "client_id": "c1", "name": "A", "status": "draft"})
    client.post("/api/menus?db=" + db_path, json={"menu_id": "m2", "client_id": "c1", "name": "B", "status": "active"})
    r = client.get("/api/menus?db=" + db_path + "&status=active")
    assert r.status_code == 200
    assert r.json()["count"] == 1
