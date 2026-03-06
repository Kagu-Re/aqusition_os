"""Production guardrails integration tests.

Verifies prod behavior: anonymous operator disabled, stricter rate limit default,
CORS prod restriction.
"""
import os
import pytest

pytestmark = pytest.mark.tenant
from fastapi.testclient import TestClient

from ae.console_app import app
from ae.public_guard import get_cors_allowlist, rate_limit_or_429, _BUCKETS


def test_anonymous_operator_disabled_in_prod(monkeypatch):
    """AE_ENV=prod, AE_CONSOLE_SECRET=secret; GET /api/health with no session, no secret -> 401."""
    monkeypatch.setenv("AE_ENV", "prod")
    monkeypatch.setenv("AE_CONSOLE_SECRET", "secret")
    monkeypatch.setenv("AE_DB_PATH", "data/acq.db")  # avoid prod DB path error

    c = TestClient(app)
    r = c.get("/api/health")
    assert r.status_code == 401


def test_rate_limit_stricter_default_in_prod(monkeypatch):
    """AE_ENV=prod, no AE_LEAD_RL_*; rate_limit_or_429 uses 10/20 (burst=20)."""
    monkeypatch.setenv("AE_ENV", "prod")
    monkeypatch.delenv("AE_LEAD_RL_PER_MIN", raising=False)
    monkeypatch.delenv("AE_LEAD_RL_BURST", raising=False)

    # Clear buckets to avoid bleed from other tests
    _BUCKETS.clear()

    from fastapi import Request
    from unittest.mock import MagicMock

    req = MagicMock(spec=Request)
    req.client = MagicMock()
    req.client.host = "127.0.0.1"
    req.headers = {}

    # With burst=20, first 20 calls succeed; 21st should 429
    for _ in range(20):
        rate_limit_or_429(req)  # should not raise

    from fastapi import HTTPException
    import pytest
    with pytest.raises(HTTPException) as exc_info:
        rate_limit_or_429(req)
    assert exc_info.value.status_code == 429


def test_cors_prod_rejects_star(monkeypatch):
    """AE_ENV=prod, AE_PUBLIC_CORS_ORIGINS='*'; get_cors_allowlist() returns []."""
    monkeypatch.setenv("AE_ENV", "prod")
    monkeypatch.setenv("AE_PUBLIC_CORS_ORIGINS", '["*"]')  # JSON list for pydantic-settings

    from ae.public_guard import _is_prod
    assert _is_prod()

    # get_cors_allowlist: when prod and '*' in origins, returns []
    result = get_cors_allowlist()
    assert result == []


def test_require_api_key_public_in_prod(monkeypatch, tmp_path):
    """AE_REQUIRE_API_KEY_PUBLIC=1, AE_ENV=prod; POST /lead without key -> 401."""
    db_path = str(tmp_path / "ae.db")
    from ae.db import init_db
    init_db(db_path)

    monkeypatch.setenv("AE_ENV", "prod")
    monkeypatch.setenv("AE_REQUIRE_API_KEY_PUBLIC", "1")
    monkeypatch.setenv("AE_DB_PATH", db_path)

    c = TestClient(app)
    r = c.post(
        "/lead",
        params={"db": db_path},
        json={"name": "Test", "email": "t@x.com", "phone": "+66123456789"},
    )
    assert r.status_code == 401
    assert "api_key" in (r.json().get("detail") or "").lower()
