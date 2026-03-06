from __future__ import annotations

"""Timeline projection engine (v1).

Projects operational events (op_events) into human-friendly timeline items.

Design goals (v1):
- deterministic: op_events ORDER BY occurred_at ASC
- composable: can union multiple event streams (aggregate + correlation)
- shallow formatting: label mapping is registry-driven
"""

from typing import List, Optional

from .models import OpEvent, TimelineItem
from .repo_op_events import list_op_events
from .timeline_registry import get_timeline_spec, render_label


def project_timeline(
    db_path: str,
    *,
    aggregate_type: Optional[str] = None,
    aggregate_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    limit: int = 500,
) -> List[TimelineItem]:
    """Project timeline items.

    If both an aggregate and a correlation_id are provided, the result is a
    union of both streams (deduped by event_id).
    """

    events: List[OpEvent] = []

    if aggregate_type is not None or aggregate_id is not None:
        if not aggregate_type or not aggregate_id:
            raise ValueError("aggregate_type and aggregate_id must be provided together")
        events.extend(
            list_op_events(
                db_path,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                limit=limit,
            )
        )

    if correlation_id is not None:
        events.extend(list_op_events(db_path, correlation_id=correlation_id, limit=limit))

    # Deduplicate while preserving chronological ordering.
    # We sort first (stable) then keep the first instance per event_id.
    events = sorted(events, key=lambda e: e.occurred_at)
    seen: set[str] = set()
    uniq: List[OpEvent] = []
    for e in events:
        if e.event_id in seen:
            continue
        seen.add(e.event_id)
        uniq.append(e)

    return [to_timeline_item(e) for e in uniq][: int(limit)]


def to_timeline_item(ev: OpEvent) -> TimelineItem:
    spec = get_timeline_spec(ev.topic)
    if spec is None:
        label = ev.topic
    else:
        label = render_label(spec.label_template, ev.payload)

    return TimelineItem(
        occurred_at=ev.occurred_at,
        event_id=ev.event_id,
        topic=ev.topic,
        label=label,
        aggregate_type=ev.aggregate_type,
        aggregate_id=ev.aggregate_id,
        payload=ev.payload,
        actor=ev.actor,
        correlation_id=ev.correlation_id,
        causation_id=ev.causation_id,
    )
