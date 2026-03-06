from __future__ import annotations

# repo.py is kept as a backward-compatible façade.
# Domain-specific DB functions live in repo_*.py modules.

from .repo_clients import upsert_client, get_client, set_client_status
from .repo_templates import upsert_template, get_template
from .repo_pages import (
    upsert_page, get_page, update_page_status, bump_content_version, list_pages, list_pages_filtered
)
from .repo_logs import (
    insert_publish_log, insert_change_log, get_last_successful_publish_log
)
from .repo_work import upsert_work_item, list_work
from .repo_events import insert_event, has_validated_events, list_events
from .repo_bulk import insert_bulk_op, try_claim_bulk_op, update_bulk_op, get_bulk_op
from .repo_stats import (
    insert_ad_stat, sum_ad_stats, revenue_stats,
    insert_spend_daily, list_spend_daily, roas_stats, upsert_spend_daily, update_spend_daily
)
from .repo_activity import append_activity, list_activity
from .repo_abuse import insert_abuse, list_abuse, export_abuse_csv
from .repo_leads import insert_lead, list_leads, get_lead, update_lead_outcome
from .repo_payments import (
    create_payment, get_payment, list_payments, update_payment_status,
    get_payment_reconciliation, upsert_payment_reconciliation, list_payments_reconciliation,
)

from .repo_chat_channels import (
    upsert_chat_channel, get_chat_channel, list_chat_channels, delete_chat_channel,
)

from .repo_chat_conversations import (
    get_or_create_conversation as get_or_create_chat_conversation,
    get_conversation as get_chat_conversation,
    list_conversations as list_chat_conversations,
)
from .repo_chat_messages import (
    insert_message as insert_chat_message,
    list_messages as list_chat_messages,
)
from .repo_chat_templates import (
    upsert_template as upsert_chat_template,
    get_template as get_chat_template,
    list_templates as list_chat_templates,
)
from .repo_menus import upsert_menu, get_menu, list_menus, upsert_menu_section, list_menu_sections, upsert_menu_item, list_menu_items
from .repo_service_packages import (
    create_package, get_package, list_packages, update_package, delete_package,
    list_packages_filtered, bulk_update_active, bulk_update_price, bulk_delete_packages
)
from .repo_booking_requests import create_booking_request, get_booking_request, get_booking_request_client_id, list_booking_requests, update_booking_status
from .repo_payment_intents import create_payment_intent, get_payment_intent, get_payment_intent_client_id, list_payment_intents, mark_payment_intent_paid
from .repo_qr import (
    create_qr_attribution, get_qr_attribution, list_qr_attributions,
    insert_qr_scan, list_qr_scans,
)
from .repo_chat_automations import (
    create_automation as create_chat_automation,
    list_automations as list_chat_automations,
    list_due_automations as list_due_chat_automations,
    list_due_automations as list_due_chat_automations,
    mark_sent as mark_chat_automation_sent,
)

from .repo_bookings import (
    create_customer, get_customer,
    create_booking, update_booking_status, get_money_board_bookings
)

from .repo_export_schemas import (
    upsert_export_schema, get_export_schema, list_export_schemas,
)

from .repo_alerts import (
    delete_spend_daily,
    get_spend_daily_client_id,
    kpi_stats,
    campaign_stats,
    simulate_budget,
    get_thresholds,
    set_thresholds,
    list_alerts,
    evaluate_alerts,
    list_playbooks,
    recommend_playbook,
    get_notify_config,
    set_notify_config,
    notify_alerts,
    test_notify,
    ack_alert,
    resolve_alert,
    list_clients,
)


__all__ = [
    "upsert_client",
    "get_client",
    "set_client_status",
    "upsert_template",
    "get_template",
    "upsert_page",
    "get_page",
    "update_page_status",
    "bump_content_version",
    "list_pages",
    "list_pages_filtered",
    "insert_publish_log",
    "insert_change_log",
    "get_last_successful_publish_log",
    "upsert_work_item",
    "list_work",
    "insert_event",
    "has_validated_events",
    "list_events",
    "insert_bulk_op",
    "try_claim_bulk_op",
    "update_bulk_op",
    "get_bulk_op",
    "insert_ad_stat",
    "sum_ad_stats",
    "revenue_stats",
    "insert_spend_daily",
    "list_spend_daily",
    "roas_stats",
    "upsert_spend_daily",
    "update_spend_daily",
    "append_activity",
    "list_activity",
    "insert_abuse",
    "list_abuse",
    "export_abuse_csv",
    "insert_lead",
    "list_leads",
    "get_lead",
    "update_lead_outcome",
    "upsert_chat_channel",
    "get_chat_channel",
    "list_chat_channels",
    "delete_spend_daily",
    "get_spend_daily_client_id",
    "kpi_stats",
    "campaign_stats",
    "simulate_budget",
    "get_thresholds",
    "set_thresholds",
    "list_alerts",
    "evaluate_alerts",
    "list_playbooks",
    "recommend_playbook",
    "get_notify_config",
    "set_notify_config",
    "notify_alerts",
    "test_notify",
    "ack_alert",
    "resolve_alert",
    "list_clients",
    "upsert_export_schema",
    "get_export_schema",
    "list_export_schemas",
    "create_package",
    "get_package",
    "list_packages",
    "update_package",
    "delete_package",
    "list_packages_filtered",
    "bulk_update_active",
    "bulk_update_price",
    "bulk_delete_packages",
    "create_customer",
    "get_customer",
    "create_booking",
    "update_booking_status",
    "get_money_board_bookings",
]

# --- onboarding templates (client-specific) ---

DEFAULT_ONBOARDING_TEMPLATES: dict[str, str] = {
    "utm_policy_md": """# UTM Policy (v1)

Goal: keep attribution **consistent** and auditable across Meta/Google/organic.

## Minimum fields (recommended)
- utm_source: platform (meta|google|tiktok|line|organic|referral)
- utm_medium: paid|organic|referral|email|social
- utm_campaign: campaign slug (lowercase, dash)
- utm_content: ad/creative slug OR placement
- utm_term: keyword (google) OR audience segment label (meta)

## Naming rules
- lowercase, dash separated
- avoid spaces / unicode
- keep campaign name stable; iterate via utm_content

## Example
?utm_source=google&utm_medium=paid&utm_campaign=cm-barber-feb&utm_content=headline-a&utm_term=barber-near-me
""",
    "naming_policy_md": """# Naming Policy (v1)

This is a *guardrail* against data entropy.

## Objects
- client_id: stable ID (e.g., cm-barber-001)
- page_id: stable slug (e.g., cm-barber-oldtown)
- campaign_id: stable slug (e.g., cm-barber-search)

## Conventions
- lowercase, dash separated
- include geo when it matters (city/area)
- avoid dates in IDs unless the object is *time-boxed*

## Recommended prefixes
- pages: p-
- campaigns: c-
- alerts: a-
""",
    "event_map_md": """# Event Map (v1)

Events are funnel markers. Keep them **few** and **reliable**.

## Core events
1) page_view
2) lead_submit (form success)
3) booking_confirmed (manual or via integration)
4) repeat_booking (retention)

## Properties (non-PII)
- page_id
- client_id
- offer_id (if relevant)
- channel (meta/google/organic/referral)
- value_bucket (low|mid|high) (optional)

## Notes
- Do not store personal identifiers in events.
- If you use GA4: map these to GA4 events with the same names.
""",
}


def get_onboarding_template(db_path: str, client_id: str, template_key: str) -> str | None:
    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "SELECT content FROM onboarding_templates WHERE client_id=? AND template_key=?",
            (client_id, template_key),
        )
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def list_onboarding_templates(db_path: str, client_id: str) -> dict[str, str]:
    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "SELECT template_key, content FROM onboarding_templates WHERE client_id=?",
            (client_id,),
        )
        rows = cur.fetchall()
        return {k: v for k, v in rows}
    finally:
        conn.close()


def upsert_onboarding_template(db_path: str, client_id: str, template_key: str, content: str) -> None:
    import sqlite3
    from datetime import datetime, timezone
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO onboarding_templates (client_id, template_key, content, updated_utc) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(client_id, template_key) DO UPDATE SET content=excluded.content, updated_utc=excluded.updated_utc",
            (client_id, template_key, content, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def ensure_default_onboarding_templates(db_path: str, client_id: str) -> dict[str, str]:
    """Populate missing templates for a client; returns final dict."""
    existing = list_onboarding_templates(db_path, client_id)
    for k, v in DEFAULT_ONBOARDING_TEMPLATES.items():
        if k not in existing:
            upsert_onboarding_template(db_path, client_id, k, v)
            existing[k] = v
    return existing


# reliability: hook retries
from .repo_hook_retries import (
    enqueue_hook_retry,
    list_due_hook_retries,
    list_hook_retries,
    get_hook_retry,
    mark_hook_retry,
)


# reliability: integrity reports
from .repo_integrity_reports import (
    insert_integrity_report,
    get_integrity_report,
    get_latest_integrity_report,
)
