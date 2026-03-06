from datetime import datetime

import pytest

from ae import db
from ae.event_bus import EventBus
from ae.repo_op_events import list_op_events
from ae.models import OpEvent


def test_op_event_bus_persists_and_orders(tmp_path):
    db_path = str(tmp_path / "ae.db")
    db.init_db(db_path)

    t1 = datetime(2026, 2, 5, 0, 0, 0)
    t2 = datetime(2026, 2, 5, 0, 0, 1)

    EventBus.emit_topic(
        db_path,
        topic="op.test.created",
        aggregate_type="lead",
        aggregate_id="L1",
        payload={"x": 1},
        occurred_at=t2,
    )
    EventBus.emit_topic(
        db_path,
        topic="op.test.created",
        aggregate_type="lead",
        aggregate_id="L1",
        payload={"x": 2},
        occurred_at=t1,
    )

    events = list_op_events(db_path, aggregate_type="lead", aggregate_id="L1")
    assert [e.payload["x"] for e in events] == [2, 1]


def test_op_event_bus_rejects_unknown_topic(tmp_path):
    db_path = str(tmp_path / "ae.db")
    db.init_db(db_path)

    with pytest.raises(ValueError):
        EventBus.emit_topic(
            db_path,
            topic="op.unknown.topic",
            aggregate_type="lead",
            aggregate_id="L1",
            payload={},
        )


def test_op_event_bus_rejects_missing_required_keys(tmp_path):
    db_path = str(tmp_path / "ae.db")
    db.init_db(db_path)

    with pytest.raises(ValueError):
        EventBus.emit_topic(
            db_path,
            topic="op.test.created",
            aggregate_type="lead",
            aggregate_id="L1",
            payload={},
        )


def test_op_event_bus_rejects_schema_version_mismatch(tmp_path):
    db_path = str(tmp_path / "ae.db")
    db.init_db(db_path)

    ev = OpEvent(
        event_id="00000000-0000-0000-0000-000000000000",
        occurred_at=datetime(2026, 2, 5, 0, 0, 0),
        topic="op.test.created",
        schema_version=2,
        aggregate_type="lead",
        aggregate_id="L1",
        payload={"x": 1},
    )

    with pytest.raises(ValueError):
        EventBus.emit(db_path, ev)
