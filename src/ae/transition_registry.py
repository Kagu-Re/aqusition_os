from __future__ import annotations

"""Transition policy registry (code-first, v1).

A transition policy defines:
- which topics are allowed to move an aggregate between states
- what the allowed state graph is

v1 is intentionally minimal: only declared topics that appear here enforce transitions.
Topics not listed here do not affect state.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


NONE_STATE = "__none__"


@dataclass(frozen=True)
class TransitionRule:
    topic: str
    from_state: str
    to_state: str


# Registry keyed by aggregate_type, then topic.
# Only topics present here are enforced / cause state changes.
REGISTRY: Dict[str, Dict[str, TransitionRule]] = {
    "lead": {
        "op.lead.created": TransitionRule(topic="op.lead.created", from_state=NONE_STATE, to_state="new"),
    },
    "booking": {
        "op.booking.created": TransitionRule(topic="op.booking.created", from_state=NONE_STATE, to_state="created"),
        "op.booking.confirmed": TransitionRule(topic="op.booking.confirmed", from_state="created", to_state="confirmed"),
        "op.booking.cancelled": TransitionRule(topic="op.booking.cancelled", from_state="created", to_state="cancelled"),
        "op.booking.completed": TransitionRule(topic="op.booking.completed", from_state="confirmed", to_state="completed"),
    },
    "payment": {
        # Payment lifecycle is modeled as a state machine over PaymentStatus-like values.
        "op.payment.created": TransitionRule(topic="op.payment.created", from_state=NONE_STATE, to_state="pending"),
        "op.payment.authorized": TransitionRule(topic="op.payment.authorized", from_state="pending", to_state="authorized"),
        "op.payment.captured": TransitionRule(topic="op.payment.captured", from_state="authorized", to_state="captured"),
        "op.payment.captured_direct": TransitionRule(topic="op.payment.captured_direct", from_state="pending", to_state="captured"),
        "op.payment.failed": TransitionRule(topic="op.payment.failed", from_state="pending", to_state="failed"),
        "op.payment.failed_after_authorized": TransitionRule(topic="op.payment.failed_after_authorized", from_state="authorized", to_state="failed"),
        "op.payment.cancelled": TransitionRule(topic="op.payment.cancelled", from_state="pending", to_state="cancelled"),
        "op.payment.cancelled_after_authorized": TransitionRule(topic="op.payment.cancelled_after_authorized", from_state="authorized", to_state="cancelled"),
        "op.payment.refunded": TransitionRule(topic="op.payment.refunded", from_state="captured", to_state="refunded"),

    },
    "booking_request": {
        "op.booking.requested": TransitionRule(topic="op.booking.requested", from_state=NONE_STATE, to_state="requested"),
        "op.booking.deposit_requested": TransitionRule(topic="op.booking.deposit_requested", from_state="requested", to_state="deposit_requested"),
        "op.booking.confirmed": TransitionRule(topic="op.booking.confirmed", from_state="deposit_requested", to_state="confirmed"),
        "op.booking.completed": TransitionRule(topic="op.booking.completed", from_state="confirmed", to_state="completed"),
        "op.booking.closed": TransitionRule(topic="op.booking.closed", from_state="completed", to_state="closed"),
    },
    "payment_intent": {
        "op.payment_intent.requested": TransitionRule(topic="op.payment_intent.requested", from_state=NONE_STATE, to_state="requested"),
        "op.payment_intent.paid": TransitionRule(topic="op.payment_intent.paid", from_state="requested", to_state="paid"),
    },
}


def get_rule(aggregate_type: str, topic: str) -> Optional[TransitionRule]:
    return REGISTRY.get(aggregate_type, {}).get(topic)


def list_rules(aggregate_type: str) -> List[TransitionRule]:
    return list(REGISTRY.get(aggregate_type, {}).values())
