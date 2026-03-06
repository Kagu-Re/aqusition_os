from datetime import datetime

import pytest

from ae import db
from ae.event_bus import EventBus
from ae.timeline_engine import project_timeline


def test_timeline_projects_labels_and_orders(tmp_path):
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
        correlation_id="CORR",
    )
    EventBus.emit_topic(
        db_path,
        topic="op.test.created",
        aggregate_type="booking",
        aggregate_id="B1",
        payload={"x": 2},
        occurred_at=t1,
        correlation_id="CORR",
    )

    items = project_timeline(db_path, correlation_id="CORR")
    assert [i.payload["x"] for i in items] == [2, 1]
    assert items[0].label == "Test created (x=2)"


def test_timeline_requires_complete_aggregate_filter(tmp_path):
    db_path = str(tmp_path / "ae.db")
    db.init_db(db_path)

    with pytest.raises(ValueError):
        project_timeline(db_path, aggregate_type="lead")
