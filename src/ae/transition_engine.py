from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import OpEvent
from .repo_states import get_state, upsert_state
from .transition_registry import NONE_STATE, get_rule


class TransitionViolation(RuntimeError):
    pass


@dataclass(frozen=True)
class TransitionResult:
    applied: bool
    prior_state: Optional[str]
    new_state: Optional[str]


def validate_and_apply(db_path: str, event: OpEvent) -> TransitionResult:
    """Validate a state transition for an event and materialize state if applicable.

    - Only topics declared in the transition registry are enforced.
    - For unregistered topics, this is a no-op (applied=False).

    Raises TransitionViolation if a declared transition is invalid.
    """
    rule = get_rule(event.aggregate_type, event.topic)
    if rule is None:
        return TransitionResult(applied=False, prior_state=get_state(db_path, aggregate_type=event.aggregate_type, aggregate_id=event.aggregate_id), new_state=None)

    current = get_state(db_path, aggregate_type=event.aggregate_type, aggregate_id=event.aggregate_id)
    cur = current or NONE_STATE
    if cur != rule.from_state:
        raise TransitionViolation(
            f"Illegal transition for {event.aggregate_type}:{event.aggregate_id} via {event.topic}: got from_state={cur}, expected {rule.from_state}"
        )

    upsert_state(
        db_path,
        aggregate_type=event.aggregate_type,
        aggregate_id=event.aggregate_id,
        state=rule.to_state,
        updated_at=event.occurred_at,
        last_event_id=event.event_id,
        last_topic=event.topic,
        last_occurred_at=event.occurred_at,
    )

    return TransitionResult(applied=True, prior_state=current, new_state=rule.to_state)
