from __future__ import annotations

"""Operational event registry (code-first, v1).

The registry is a safety gate:
- Topics must be declared before emission
- schema_version is enforced
- required payload keys are enforced (v1: shallow validation)

Governance/versioning enhancements land in OP-GOV-001+.
"""

from typing import Dict

from .models import EventSpec


# Minimal seed registry. Extend as modules come online.
REGISTRY: Dict[str, EventSpec] = {
    # lead lifecycle
    "op.lead.created": EventSpec(topic="op.lead.created", schema_version=1, required_keys=[]),

    # booking lifecycle
    "op.booking.created": EventSpec(topic="op.booking.created", schema_version=1, required_keys=["booking_id", "lead_id"]),
    "op.booking.confirmed": EventSpec(topic="op.booking.confirmed", schema_version=1, required_keys=["booking_id", "lead_id"]),
    "op.booking.cancelled": EventSpec(topic="op.booking.cancelled", schema_version=1, required_keys=["booking_id", "lead_id"]),
    "op.booking.completed": EventSpec(topic="op.booking.completed", schema_version=1, required_keys=["booking_id", "lead_id"]),
    # booking request lifecycle (money board)
    "op.booking.requested": EventSpec(topic="op.booking.requested", schema_version=1, required_keys=["request_id", "lead_id"]),
    "op.booking.deposit_requested": EventSpec(topic="op.booking.deposit_requested", schema_version=1, required_keys=["request_id", "lead_id"]),
    "op.booking.closed": EventSpec(topic="op.booking.closed", schema_version=1, required_keys=["request_id", "lead_id"]),
    # payment intent lifecycle
    "op.payment_intent.requested": EventSpec(topic="op.payment_intent.requested", schema_version=1, required_keys=["intent_id", "lead_id"]),
    "op.payment_intent.paid": EventSpec(topic="op.payment_intent.paid", schema_version=1, required_keys=["intent_id", "lead_id"]),

    # payment lifecycle
    "op.payment.created": EventSpec(
        topic="op.payment.created",
        schema_version=1,
        required_keys=["payment_id", "booking_id", "lead_id", "amount", "currency", "status"],
    ),
    "op.payment.status_changed": EventSpec(
        topic="op.payment.status_changed",
        schema_version=1,
        required_keys=["payment_id", "lead_id", "from_status", "to_status"],
    ),
    "op.payment.authorized": EventSpec(topic="op.payment.authorized", schema_version=1, required_keys=["payment_id", "lead_id", "status"]),
    "op.payment.captured": EventSpec(topic="op.payment.captured", schema_version=1, required_keys=["payment_id", "lead_id", "status"]),
    "op.payment.captured_direct": EventSpec(topic="op.payment.captured_direct", schema_version=1, required_keys=["payment_id", "lead_id", "status"]),
    "op.payment.failed": EventSpec(topic="op.payment.failed", schema_version=1, required_keys=["payment_id", "lead_id", "status"]),
    "op.payment.failed_after_authorized": EventSpec(topic="op.payment.failed_after_authorized", schema_version=1, required_keys=["payment_id", "lead_id", "status"]),
    "op.payment.cancelled": EventSpec(topic="op.payment.cancelled", schema_version=1, required_keys=["payment_id", "lead_id", "status"]),
    "op.payment.cancelled_after_authorized": EventSpec(topic="op.payment.cancelled_after_authorized", schema_version=1, required_keys=["payment_id", "lead_id", "status"]),
    "op.payment.refunded": EventSpec(topic="op.payment.refunded", schema_version=1, required_keys=["payment_id", "lead_id", "status"]),

    # SLA
    "op.sla.warning": EventSpec(topic="op.sla.warning", schema_version=1, required_keys=["rule_id", "aggregate_type", "aggregate_id"]),
    "op.sla.breach": EventSpec(topic="op.sla.breach", schema_version=1, required_keys=["rule_id", "aggregate_type", "aggregate_id"]),


    # chat
    "op.chat.conversation_opened": EventSpec(topic="op.chat.conversation_opened", schema_version=1, required_keys=["conversation_id"]),
    "op.chat.message_received": EventSpec(topic="op.chat.message_received", schema_version=1, required_keys=["conversation_id", "text"]),
    "op.chat.message_sent": EventSpec(topic="op.chat.message_sent", schema_version=1, required_keys=["conversation_id", "text"]),


    # QR
    "op.qr.generated": EventSpec(topic="op.qr.generated", schema_version=1, required_keys=["attribution_id", "kind", "url"]),
    "op.qr.scanned": EventSpec(topic="op.qr.scanned", schema_version=1, required_keys=["attribution_id", "url"]),
    # reliability
    "op.rel.integrity.checked": EventSpec(topic="op.rel.integrity.checked", schema_version=1, required_keys=["report_id", "status", "issue_count"]),
    "op.rel.integrity.failed": EventSpec(topic="op.rel.integrity.failed", schema_version=1, required_keys=["report_id", "issue_count"]),
    # CRM exports
    "op.crm.exported": EventSpec(topic="op.crm.exported", schema_version=1, required_keys=["schema_name", "row_count"]),
    "op.crm.export.file_generated": EventSpec(topic="op.crm.export.file_generated", schema_version=1, required_keys=["preset_name", "output_path", "row_count"]),
    "op.crm.sync.started": EventSpec(topic="op.crm.sync.started", schema_version=1, required_keys=["job_id", "preset_name"]),
    "op.crm.sync.completed": EventSpec(topic="op.crm.sync.completed", schema_version=1, required_keys=["job_id", "preset_name"]),
    "op.crm.sync.failed": EventSpec(topic="op.crm.sync.failed", schema_version=1, required_keys=["job_id", "preset_name", "error"]),


    # reserved namespace for tests (do not rely on this in production)
    "op.test.created": EventSpec(topic="op.test.created", schema_version=1, required_keys=["x"]),
}


def get_event_spec(topic: str) -> EventSpec | None:
    return REGISTRY.get(topic)
