from __future__ import annotations

from pathlib import Path

import pytest

from ae.db import init_db
from ae.event_bus import EventBus
from ae.repo_states import get_state
from ae.transition_engine import TransitionViolation


def test_booking_transition_happy_path(tmp_path: Path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    # created -> confirmed
    EventBus.emit_topic(db_path, topic="op.booking.created", aggregate_type="booking", aggregate_id="b1", payload={"booking_id":"b1","lead_id":1})
    assert get_state(db_path, aggregate_type="booking", aggregate_id="b1") == "created"

    EventBus.emit_topic(db_path, topic="op.booking.confirmed", aggregate_type="booking", aggregate_id="b1", payload={"booking_id":"b1","lead_id":1})
    assert get_state(db_path, aggregate_type="booking", aggregate_id="b1") == "confirmed"


def test_booking_illegal_transition_rejected(tmp_path: Path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    # confirmed without created
    with pytest.raises(TransitionViolation):
        EventBus.emit_topic(db_path, topic="op.booking.confirmed", aggregate_type="booking", aggregate_id="b1", payload={"booking_id":"b1","lead_id":1})


def test_unknown_topic_does_not_change_state(tmp_path: Path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    # lead created sets state
    EventBus.emit_topic(db_path, topic="op.lead.created", aggregate_type="lead", aggregate_id="l1")
    assert get_state(db_path, aggregate_type="lead", aggregate_id="l1") == "new"

    # topic not in transition registry -> no change
    # (use op_events reserved test topic but for lead aggregate; it's not in transition registry)
    EventBus.emit_topic(db_path, topic="op.test.created", aggregate_type="lead", aggregate_id="l1", payload={"x": 1})
    assert get_state(db_path, aggregate_type="lead", aggregate_id="l1") == "new"
