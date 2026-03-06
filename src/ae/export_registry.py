from __future__ import annotations

"""Export schema registry (code-first).

OP-CRM-001A.

Schemas are flat lists of fields extracted from entities.
Entity types (v1):
- lead: lead_intake
- payment: payments

DB overrides are supported via repo_export_schemas.
"""

from .models import ExportField, ExportSchema

SCHEMAS: dict[str, ExportSchema] = {
    "leads_basic": ExportSchema(
        name="leads_basic",
        schema_version=1,
        fields=[
            ExportField(out_key="lead_id", entity="lead", path="lead_id", required=True),
            ExportField(out_key="ts", entity="lead", path="ts"),
            ExportField(out_key="source", entity="lead", path="source"),
            ExportField(out_key="client_id", entity="lead", path="client_id"),
            ExportField(out_key="name", entity="lead", path="name"),
            ExportField(out_key="phone", entity="lead", path="phone"),
            ExportField(out_key="email", entity="lead", path="email"),
            ExportField(out_key="status", entity="lead", path="status"),
            ExportField(out_key="booking_status", entity="lead", path="booking_status"),
            ExportField(out_key="utm_source", entity="lead", path="utm_source"),
            ExportField(out_key="utm_campaign", entity="lead", path="utm_campaign"),
        ],
        notes="Flat export of lead intake rows.",
    ),
    "bookings_basic": ExportSchema(
        name="bookings_basic",
        schema_version=1,
        fields=[
            ExportField(out_key="lead_id", entity="lead", path="lead_id", required=True),
            ExportField(out_key="ts", entity="lead", path="ts"),
            ExportField(out_key="client_id", entity="lead", path="client_id"),
            ExportField(out_key="name", entity="lead", path="name"),
            ExportField(out_key="phone", entity="lead", path="phone"),
            ExportField(out_key="email", entity="lead", path="email"),
            ExportField(out_key="booking_status", entity="lead", path="booking_status", required=True),
            ExportField(out_key="booking_value", entity="lead", path="booking_value"),
            ExportField(out_key="booking_currency", entity="lead", path="booking_currency"),
            ExportField(out_key="booking_ts", entity="lead", path="booking_ts"),
        ],
        notes="Lead-based view focused on booking fields (filtering is done by export_engine).",
    ),
    "payments_basic": ExportSchema(
        name="payments_basic",
        schema_version=1,
        fields=[
            ExportField(out_key="payment_id", entity="payment", path="payment_id", required=True),
            ExportField(out_key="lead_id", entity="payment", path="lead_id", required=True),
            ExportField(out_key="booking_id", entity="payment", path="booking_id", required=True),
            ExportField(out_key="amount", entity="payment", path="amount", required=True),
            ExportField(out_key="currency", entity="payment", path="currency", required=True),
            ExportField(out_key="status", entity="payment", path="status"),
            ExportField(out_key="provider", entity="payment", path="provider"),
            ExportField(out_key="method", entity="payment", path="method"),
            ExportField(out_key="external_ref", entity="payment", path="external_ref"),
            ExportField(out_key="created_at", entity="payment", path="created_at"),
        ],
        notes="Flat export of payments.",
    ),
}

def get_schema(name: str) -> ExportSchema:
    if name not in SCHEMAS:
        raise KeyError(f"unknown export schema: {name}")
    return SCHEMAS[name]
