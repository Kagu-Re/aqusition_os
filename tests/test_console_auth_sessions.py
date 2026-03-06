from fastapi.testclient import TestClient

from ae.console_app import app
from ae.db import init_db
from ae.auth import create_user


def test_login_sets_cookie_and_me_works(tmp_path, monkeypatch):
    db = tmp_path / "acq.db"
    init_db(str(db))
    create_user(str(db), username="admin", password="pw12345", role="admin")

    monkeypatch.setenv("AE_DB_PATH", str(db))
    monkeypatch.setenv("AE_CONSOLE_SECRET", "")  # force session path

    c = TestClient(app)

    r = c.post("/api/auth/login", json={"username": "admin", "password": "pw12345"})
    assert r.status_code == 200
    assert "ae_session" in r.cookies
    assert "ae_csrf" in r.cookies

    r2 = c.get("/api/auth/me", cookies={"ae_session": r.cookies.get("ae_session")})
    assert r2.status_code == 200
    assert r2.json()["username"] == "admin"
    assert r2.json()["role"] == "admin"


def test_health_allows_anon_in_dev_mode(monkeypatch):
    monkeypatch.setenv("AE_CONSOLE_SECRET", "")
    c = TestClient(app)
    r = c.get("/api/health")
    assert r.status_code == 200


def test_viewer_forbidden_on_bulk(tmp_path, monkeypatch):
    db = tmp_path / "acq.db"
    init_db(str(db))
    create_user(str(db), username="view", password="pw12345", role="viewer")

    monkeypatch.setenv("AE_DB_PATH", str(db))
    monkeypatch.setenv("AE_CONSOLE_SECRET", "")

    c = TestClient(app)
    r = c.post("/api/auth/login", json={"username": "view", "password": "pw12345"})
    sid = r.cookies.get("ae_session")

    csrf = r.cookies.get("ae_csrf")

    r2 = c.post("/api/bulk/run", json={"action": "validate", "selector": {"page_ids": []}, "mode": "dry_run"}, cookies={"ae_session": sid, "ae_csrf": csrf}, headers={"X-AE-CSRF": csrf})
    assert r2.status_code == 403
