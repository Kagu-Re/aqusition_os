from __future__ import annotations

from pathlib import Path

from ae.db import init_db
from ae.event_bus import EventBus
from ae.hooks import GLOBAL_HOOKS
from ae.repo_activity import list_activity
from ae import repo


def test_hook_dispatch_called(tmp_path: Path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    GLOBAL_HOOKS._hooks.clear()  # noqa: SLF001

    called = {"n": 0}

    def hook(db_path: str, event):
        called["n"] += 1

    GLOBAL_HOOKS.subscribe(name="h1", pattern="op.lead.*", fn=hook)

    EventBus.emit_topic(db_path, topic="op.lead.created", aggregate_type="lead", aggregate_id="l1")

    assert called["n"] == 1


def test_hook_errors_are_logged(tmp_path: Path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    GLOBAL_HOOKS._hooks.clear()  # noqa: SLF001

    def bad_hook(db_path: str, event):
        raise RuntimeError("boom")

    GLOBAL_HOOKS.subscribe(name="bad", pattern="op.lead.created", fn=bad_hook)

    # should not raise
    EventBus.emit_topic(db_path, topic="op.lead.created", aggregate_type="lead", aggregate_id="l1")

    acts = list_activity(db_path, limit=50, action="hook_error")

    retries = repo.list_hook_retries(db_path, status="pending", limit=10)
    assert len(retries) == 1
    assert retries[0].hook_name == "bad"

    assert len(acts) >= 1
    assert acts[0].details_json.get("hook") == "bad"
