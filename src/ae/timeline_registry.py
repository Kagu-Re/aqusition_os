from __future__ import annotations

"""Timeline registry (code-first, v1).

Maps operational event topics to human-friendly labels for projection.
This is intentionally shallow in v1; governance lands in OP-GOV-00x.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TimelineSpec(BaseModel):
    topic: str = Field(min_length=1)
    label_template: str = Field(min_length=1)


REGISTRY: Dict[str, TimelineSpec] = {
    "op.lead.created": TimelineSpec(topic="op.lead.created", label_template="Lead created"),

    # OP-BOOK-002B: richer booking labels (safe template rendering, missing keys -> '?')
    "op.booking.created": TimelineSpec(topic="op.booking.created", label_template="Booking created (ts={booking_ts})"),
    "op.booking.confirmed": TimelineSpec(topic="op.booking.confirmed", label_template="Booking confirmed (value={booking_value} {booking_currency})"),
    "op.booking.cancelled": TimelineSpec(topic="op.booking.cancelled", label_template="Booking cancelled (ts={booking_ts})"),
    "op.booking.completed": TimelineSpec(topic="op.booking.completed", label_template="Booking completed (ts={booking_ts})"),

    # OP-PAY-001C: payment lifecycle labels
    "op.payment.created": TimelineSpec(
        topic="op.payment.created",
        label_template="Payment created (amount={amount} {currency}, status={status})",
    ),
    "op.payment.status_changed": TimelineSpec(
        topic="op.payment.status_changed",
        label_template="Payment status changed ({from_status} → {to_status})",
    ),
    "op.payment.authorized": TimelineSpec(topic="op.payment.authorized", label_template="Payment authorized"),
    "op.payment.captured": TimelineSpec(topic="op.payment.captured", label_template="Payment captured"),
    "op.payment.captured_direct": TimelineSpec(topic="op.payment.captured_direct", label_template="Payment captured (direct)"),
    "op.payment.failed": TimelineSpec(topic="op.payment.failed", label_template="Payment failed"),
    "op.payment.failed_after_authorized": TimelineSpec(topic="op.payment.failed_after_authorized", label_template="Payment failed (after authorization)"),
    "op.payment.cancelled": TimelineSpec(topic="op.payment.cancelled", label_template="Payment cancelled"),
    "op.payment.cancelled_after_authorized": TimelineSpec(topic="op.payment.cancelled_after_authorized", label_template="Payment cancelled (after authorization)"),
    "op.payment.refunded": TimelineSpec(topic="op.payment.refunded", label_template="Payment refunded"),

    # SLA
    "op.sla.warning": TimelineSpec(topic="op.sla.warning", label_template="SLA warning ({rule_id})"),
    "op.sla.breach": TimelineSpec(topic="op.sla.breach", label_template="SLA breach ({rule_id})"),

    # tests
    "op.test.created": TimelineSpec(topic="op.test.created", label_template="Test created (x={x})"),

    # chat
    "op.chat.conversation_opened": TimelineSpec(topic="op.chat.conversation_opened", label_template="Chat opened"),
    "op.chat.message_received": TimelineSpec(topic="op.chat.message_received", label_template="Inbound message: {text}"),
    "op.chat.message_sent": TimelineSpec(topic="op.chat.message_sent", label_template="Outbound message: {text}"),
    # QR
    "op.qr.generated": TimelineSpec(topic="op.qr.generated", label_template="QR generated ({kind})"),
    "op.qr.scanned": TimelineSpec(topic="op.qr.scanned", label_template="QR scanned"),
    # reliability
    "op.rel.integrity.checked": TimelineSpec(topic="op.rel.integrity.checked", label_template="Integrity check ({status}) issues={issue_count}"),
    "op.rel.integrity.failed": TimelineSpec(topic="op.rel.integrity.failed", label_template="Integrity issues detected (count={issue_count})"),

    # OP-CRM-001A/B: export labels
    "op.crm.exported": TimelineSpec(topic="op.crm.exported", label_template="CRM export {schema_name} ({row_count} rows)"),
    "op.crm.export.file_generated": TimelineSpec(topic="op.crm.export.file_generated", label_template="CRM file generated {preset_name} ({row_count} rows)"),
    "op.crm.sync.started": TimelineSpec(topic="op.crm.sync.started", label_template="CRM sync started {preset_name}"),
    "op.crm.sync.completed": TimelineSpec(topic="op.crm.sync.completed", label_template="CRM sync completed {preset_name}"),
    "op.crm.sync.failed": TimelineSpec(topic="op.crm.sync.failed", label_template="CRM sync failed {preset_name}: {error}"),

}


def get_timeline_spec(topic: str) -> Optional[TimelineSpec]:
    return REGISTRY.get(topic)


def render_label(label_template: str, payload: Dict[str, Any]) -> str:
    """Render a label template using payload keys.

    Missing keys are replaced with '?' (v1 safety).
    """

    out = label_template
    for key in _extract_placeholders(label_template):
        value = payload.get(key)
        out = out.replace("{" + key + "}", "?" if value is None else str(value))
    return out


def _extract_placeholders(template: str) -> list[str]:
    keys: list[str] = []
    i = 0
    while i < len(template):
        if template[i] == "{":
            j = template.find("}", i + 1)
            if j == -1:
                break
            key = template[i + 1 : j].strip()
            if key and key.isidentifier():
                keys.append(key)
            i = j + 1
        else:
            i += 1
    return keys
