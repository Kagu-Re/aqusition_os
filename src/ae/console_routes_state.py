from __future__ import annotations

from fastapi import APIRouter, Query

from .console_support import _resolve_db
from .repo_states import get_state_row

router = APIRouter(prefix="/api", tags=["ops"])


@router.get("/state")
def read_state(
    db: str = Query(..., description="Path to sqlite db"),
    aggregate_type: str = Query(...),
    aggregate_id: str = Query(...),
):
    db_path = _resolve_db(db)
    row = get_state_row(db_path, aggregate_type=aggregate_type, aggregate_id=aggregate_id)
    if not row:
        return {
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "state": None,
            "updated_at": None,
            "last_event_id": None,
            "last_topic": None,
            "last_occurred_at": None,
        }
    state, updated_at, last_event_id, last_topic, last_occurred_at = row
    return {
        "aggregate_type": aggregate_type,
        "aggregate_id": aggregate_id,
        "state": state,
        "updated_at": updated_at,
        "last_event_id": last_event_id,
        "last_topic": last_topic,
        "last_occurred_at": last_occurred_at,
    }
