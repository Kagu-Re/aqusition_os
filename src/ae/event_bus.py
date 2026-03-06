from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from .models import OpEvent
from .op_event_registry import get_event_spec
from .repo_op_events import insert_op_event
from .transition_engine import validate_and_apply
from .hooks import GLOBAL_HOOKS
from .policy_audit import audit_policy_deny
from .transition_engine import TransitionViolation


class EventBus:
    """In-process event emitter with persistent append-only log (v1)."""

    @staticmethod
    def emit(db_path: str, event: OpEvent) -> None:
        try:
            spec = get_event_spec(event.topic)
            if spec is None:
                raise ValueError(f"Unregistered op event topic: {event.topic}")
            if event.schema_version != spec.schema_version:
                raise ValueError(
                    f"schema_version mismatch for {event.topic}: got {event.schema_version}, expected {spec.schema_version}"
                )
            missing = [k for k in spec.required_keys if k not in event.payload]
            if missing:
                raise ValueError(f"Missing required payload keys for {event.topic}: {missing}")

            # Enforce declared state transitions before persistence
            validate_and_apply(db_path, event)

            insert_op_event(db_path, event)
        except TransitionViolation as e:
            audit_policy_deny(
                db_path,
                policy="transition_engine",
                reason=str(e),
                subject_type=event.aggregate_type,
                subject_id=event.aggregate_id,
                event=event,
            )
            raise
        except Exception as e:
            audit_policy_deny(
                db_path,
                policy="event_bus",
                reason=str(e),
                subject_type=event.aggregate_type,
                subject_id=event.aggregate_id,
                event=event,
                meta={"topic": event.topic},
            )
            raise

        # Post-persist best-effort hooks (never raise)
        try:
            GLOBAL_HOOKS.dispatch(db_path, event)
        except Exception:
            pass

    @staticmethod
    def emit_topic(
        db_path: str,
        *,
        topic: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: Optional[Dict[str, Any]] = None,
        actor: Optional[str] = None,
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
        occurred_at: Optional[datetime] = None,
    ) -> OpEvent:
        ev = OpEvent(
            event_id=str(uuid.uuid4()),
            occurred_at=occurred_at or datetime.utcnow(),
            topic=topic,
            schema_version=1,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload or {},
            actor=actor,
            correlation_id=correlation_id,
            causation_id=causation_id,
        )
        EventBus.emit(db_path, ev)
        return ev
