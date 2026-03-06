from __future__ import annotations
import os


from fastapi.testclient import TestClient

from ae.console_app import app
from ae.db import init_db


def test_list_presets_endpoint(tmp_path):
    os.environ.pop("AE_CONSOLE_SECRET", None)
    db = str(tmp_path / "t.db")
    init_db(db)
    c = TestClient(app)
    r = c.get("/api/exports/presets", params={"db": db})
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    names = {i["name"] for i in data["items"]}
    assert "leads_csv_basic" in names


def test_run_preset_generates_file(tmp_path):
    os.environ.pop("AE_CONSOLE_SECRET", None)
    db = str(tmp_path / "t.db")
    init_db(db)
    c = TestClient(app)
    out_dir = str(tmp_path / "out")
    r = c.post("/api/exports/run-preset/leads_csv_basic", params={"db": db, "output_dir": out_dir})
    assert r.status_code == 200
    payload = r.json()
    assert payload["output_path"].endswith(".csv")
