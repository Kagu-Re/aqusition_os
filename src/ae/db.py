from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from datetime import datetime

SCHEMA_SQL = [
    # registries
    """CREATE TABLE IF NOT EXISTS clients (
        client_id TEXT PRIMARY KEY,
        client_name TEXT NOT NULL,
        trade TEXT NOT NULL,
        business_model TEXT NOT NULL DEFAULT 'quote_based',
        geo_country TEXT NOT NULL,
        geo_city TEXT NOT NULL,
        service_area_json TEXT NOT NULL,
        primary_phone TEXT NOT NULL,
        lead_email TEXT NOT NULL,
        status TEXT NOT NULL,
        hours TEXT,
        license_badges_json TEXT NOT NULL,
        price_anchor TEXT,
        brand_theme TEXT,
        notes_internal TEXT,
        service_config_json TEXT NOT NULL DEFAULT '{}'
    );""",
    """CREATE TABLE IF NOT EXISTS onboarding_templates (
        client_id TEXT NOT NULL,
        template_key TEXT NOT NULL,
        content TEXT NOT NULL,
        updated_utc TEXT NOT NULL,
        PRIMARY KEY (client_id, template_key)
    );""",

    """CREATE TABLE IF NOT EXISTS templates (
        template_id TEXT PRIMARY KEY,
        template_name TEXT NOT NULL,
        template_version TEXT NOT NULL,
        cms_schema_version TEXT NOT NULL,
        compatible_events_version TEXT NOT NULL,
        status TEXT NOT NULL,
        changelog TEXT,
        preview_url TEXT
    );""",
    """CREATE TABLE IF NOT EXISTS pages (
        page_id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        template_id TEXT NOT NULL,
        template_version TEXT NOT NULL,
        page_slug TEXT NOT NULL,
        page_url TEXT NOT NULL,
        page_status TEXT NOT NULL,
        content_version INTEGER NOT NULL,
        service_focus TEXT,
        locale TEXT NOT NULL,
        FOREIGN KEY(client_id) REFERENCES clients(client_id),
        FOREIGN KEY(template_id) REFERENCES templates(template_id)
    );""",
    """CREATE TABLE IF NOT EXISTS assets (
        asset_id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        asset_type TEXT NOT NULL,
        source TEXT NOT NULL,
        url TEXT NOT NULL,
        license_info TEXT,
        alt_text TEXT,
        checksum TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(client_id)
    );""",

    
    # menus / QR
    """CREATE TABLE IF NOT EXISTS menus (
        menu_id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        name TEXT NOT NULL,
        language TEXT NOT NULL,
        currency TEXT NOT NULL,
        status TEXT NOT NULL,
        meta_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(client_id) REFERENCES clients(client_id)
    );""",
    """CREATE INDEX IF NOT EXISTS idx_menus_client ON menus(client_id, updated_at);""",
    """CREATE TABLE IF NOT EXISTS menu_sections (
        section_id TEXT PRIMARY KEY,
        menu_id TEXT NOT NULL,
        title TEXT NOT NULL,
        sort_order INTEGER NOT NULL,
        FOREIGN KEY(menu_id) REFERENCES menus(menu_id)
    );""",
    """CREATE INDEX IF NOT EXISTS idx_menu_sections_menu ON menu_sections(menu_id, sort_order);""",
    """CREATE TABLE IF NOT EXISTS menu_items (
        item_id TEXT PRIMARY KEY,
        menu_id TEXT NOT NULL,
        section_id TEXT,
        title TEXT NOT NULL,
        description TEXT,
        price REAL,
        currency TEXT,
        is_available INTEGER NOT NULL,
        sort_order INTEGER NOT NULL,
        meta_json TEXT NOT NULL,
        FOREIGN KEY(menu_id) REFERENCES menus(menu_id),
        FOREIGN KEY(section_id) REFERENCES menu_sections(section_id)
    );""",
    """CREATE INDEX IF NOT EXISTS idx_menu_items_menu ON menu_items(menu_id, sort_order);""",
    """CREATE INDEX IF NOT EXISTS idx_menu_items_section ON menu_items(section_id, sort_order);""",

    # service packages
    """CREATE TABLE IF NOT EXISTS service_packages (
        package_id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        duration_min INTEGER NOT NULL,
        addons_json TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        meta_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(client_id) REFERENCES clients(client_id)
    );""",
    """CREATE INDEX IF NOT EXISTS idx_service_packages_client_active ON service_packages(client_id, active);""",

    # booking requests
    """CREATE TABLE IF NOT EXISTS booking_requests (
        request_id TEXT PRIMARY KEY,
        lead_id INTEGER NOT NULL,
        package_id TEXT NOT NULL,
        preferred_window TEXT,
        location TEXT,
        status TEXT NOT NULL,
        meta_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(lead_id) REFERENCES lead_intake(lead_id),
        FOREIGN KEY(package_id) REFERENCES service_packages(package_id)
    );""",
    """CREATE INDEX IF NOT EXISTS idx_booking_requests_lead ON booking_requests(lead_id);""",
    """CREATE INDEX IF NOT EXISTS idx_booking_requests_status ON booking_requests(status, updated_at);""",
    """CREATE INDEX IF NOT EXISTS idx_booking_requests_package ON booking_requests(package_id);""",

    # payment intents
    """CREATE TABLE IF NOT EXISTS payment_intents (
        intent_id TEXT PRIMARY KEY,
        lead_id INTEGER NOT NULL,
        booking_request_id TEXT NOT NULL,
        amount REAL NOT NULL,
        method TEXT NOT NULL,
        status TEXT NOT NULL,
        payment_link TEXT,
        meta_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(lead_id) REFERENCES lead_intake(lead_id),
        FOREIGN KEY(booking_request_id) REFERENCES booking_requests(request_id)
    );""",
    """CREATE INDEX IF NOT EXISTS idx_payment_intents_booking ON payment_intents(booking_request_id);""",
    """CREATE INDEX IF NOT EXISTS idx_payment_intents_status ON payment_intents(status, created_at);""",

    # QR attribution + scan logging
    """CREATE TABLE IF NOT EXISTS qr_attributions (
        attribution_id TEXT PRIMARY KEY,
        kind TEXT NOT NULL,
        menu_id TEXT,
        url TEXT NOT NULL,
        meta_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(menu_id) REFERENCES menus(menu_id)
    );""",
    """CREATE INDEX IF NOT EXISTS idx_qr_attr_menu_time ON qr_attributions(menu_id, created_at);""",
    """CREATE TABLE IF NOT EXISTS qr_scans (
        scan_id TEXT PRIMARY KEY,
        attribution_id TEXT NOT NULL,
        ts TEXT NOT NULL,
        meta_json TEXT NOT NULL,
        FOREIGN KEY(attribution_id) REFERENCES qr_attributions(attribution_id)
    );""",
    """CREATE INDEX IF NOT EXISTS idx_qr_scans_attr_time ON qr_scans(attribution_id, ts);""",


# chat channels (registry)
    """CREATE TABLE IF NOT EXISTS chat_channels (
        channel_id TEXT PRIMARY KEY,
        provider TEXT NOT NULL,
        handle TEXT NOT NULL,
        display_name TEXT,
        meta_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    );""",
    """CREATE INDEX IF NOT EXISTS idx_chat_channels_provider_handle ON chat_channels(provider, handle);""",
    # chat conversations/messages/templates/automations
    """CREATE TABLE IF NOT EXISTS chat_conversations (
        conversation_id TEXT PRIMARY KEY,
        channel_id TEXT NOT NULL,
        external_thread_id TEXT,
        lead_id TEXT,
        booking_id TEXT,
        status TEXT NOT NULL,
        meta_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );""",
    """CREATE INDEX IF NOT EXISTS idx_chat_conversations_channel_thread ON chat_conversations(channel_id, external_thread_id);""",
    """CREATE INDEX IF NOT EXISTS idx_chat_conversations_lead ON chat_conversations(lead_id, created_at);""",
    """CREATE TABLE IF NOT EXISTS chat_messages (
        message_id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        direction TEXT NOT NULL,
        ts TEXT NOT NULL,
        external_msg_id TEXT,
        text TEXT,
        payload_json TEXT NOT NULL
    );""",
    """CREATE INDEX IF NOT EXISTS idx_chat_messages_conv_time ON chat_messages(conversation_id, ts);""",
    """CREATE TABLE IF NOT EXISTS chat_templates (
        template_key TEXT PRIMARY KEY,
        language TEXT NOT NULL,
        body TEXT NOT NULL,
        status TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );""",
    """CREATE INDEX IF NOT EXISTS idx_chat_templates_status ON chat_templates(status, updated_at);""",
    """CREATE TABLE IF NOT EXISTS chat_automations (
        automation_id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        template_key TEXT NOT NULL,
        due_at TEXT NOT NULL,
        status TEXT NOT NULL,
        context_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        sent_at TEXT
    );""",
    """CREATE INDEX IF NOT EXISTS idx_chat_automations_due ON chat_automations(status, due_at);""",

    # queue
    """CREATE TABLE IF NOT EXISTS work_items (
        work_item_id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        client_id TEXT NOT NULL,
        page_id TEXT,
        status TEXT NOT NULL,
        priority TEXT NOT NULL,
        owner TEXT NOT NULL,
        acceptance_criteria TEXT,
        blocker_reason TEXT,
        links_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );""",
    # logs (append-only)
    """CREATE TABLE IF NOT EXISTS publish_logs (
        log_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        client_id TEXT NOT NULL,
        page_id TEXT NOT NULL,
        template_id TEXT NOT NULL,
        template_version TEXT NOT NULL,
        content_version INTEGER NOT NULL,
        action TEXT NOT NULL,
        result TEXT NOT NULL,
        notes TEXT
    );""",
    """CREATE TABLE IF NOT EXISTS change_logs (
        log_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        client_id TEXT NOT NULL,
        page_id TEXT NOT NULL,
        content_version_before INTEGER NOT NULL,
        content_version_after INTEGER NOT NULL,
        changed_fields_json TEXT NOT NULL,
        notes TEXT
    );""",
    # event stream (synthetic or imported)
    """CREATE TABLE IF NOT EXISTS events (
        event_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        page_id TEXT NOT NULL,
        event_name TEXT NOT NULL,
        params_json TEXT NOT NULL
    );""",

    # operational event bus (internal)
    """CREATE TABLE IF NOT EXISTS op_events (
        event_id TEXT PRIMARY KEY,
        occurred_at TEXT NOT NULL,
        topic TEXT NOT NULL,
        schema_version INTEGER NOT NULL,
        aggregate_type TEXT NOT NULL,
        aggregate_id TEXT NOT NULL,
        actor TEXT,
        correlation_id TEXT,
        causation_id TEXT,
        payload_json TEXT NOT NULL
    );""",
    """CREATE INDEX IF NOT EXISTS idx_op_events_agg_time ON op_events(aggregate_type, aggregate_id, occurred_at);""",
    """CREATE INDEX IF NOT EXISTS idx_op_events_topic_time ON op_events(topic, occurred_at);""",
    """CREATE INDEX IF NOT EXISTS idx_op_events_corr_time ON op_events(correlation_id, occurred_at);""",

    # operational materialized state (latest known state per aggregate)
    """CREATE TABLE IF NOT EXISTS op_states (
        aggregate_type TEXT NOT NULL,
        aggregate_id TEXT NOT NULL,
        state TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        last_event_id TEXT,
        last_topic TEXT,
        last_occurred_at TEXT,
        PRIMARY KEY (aggregate_type, aggregate_id)
    );""",
    """CREATE INDEX IF NOT EXISTS idx_op_states_state ON op_states(aggregate_type, state, updated_at);""",

    # governance: policy audit logs (append-only)
    """CREATE TABLE IF NOT EXISTS policy_audit_logs (
        audit_id TEXT PRIMARY KEY,
        ts TEXT NOT NULL,
        policy TEXT NOT NULL,
        decision TEXT NOT NULL,
        subject_type TEXT,
        subject_id TEXT,
        topic TEXT,
        schema_version INTEGER,
        reason TEXT,
        meta_json TEXT NOT NULL
    );""",
    """CREATE INDEX IF NOT EXISTS idx_policy_audit_time ON policy_audit_logs(ts);""",
    """CREATE INDEX IF NOT EXISTS idx_policy_audit_policy ON policy_audit_logs(policy, decision, ts);""",
    # ad platform stats (optional; can be synthetic or imported)
    """CREATE TABLE IF NOT EXISTS ad_stats (
        stat_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        page_id TEXT NOT NULL,
        platform TEXT NOT NULL,
        campaign_id TEXT,
        adset_id TEXT,
        ad_id TEXT,
        impressions INTEGER,
        clicks INTEGER,
        spend REAL,
        revenue REAL
    );""",
    # bulk operations
    """CREATE TABLE IF NOT EXISTS bulk_ops (
        bulk_id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        mode TEXT NOT NULL,              -- dry_run | execute
        action TEXT NOT NULL,            -- validate | publish | pause
        selector_json TEXT NOT NULL,     -- e.g., {"page_ids": [...]} or filters
        status TEXT NOT NULL,            -- queued | running | done | failed
        result_json TEXT NOT NULL,
        notes TEXT
    );""",
    """CREATE TABLE IF NOT EXISTS activity_log (
        activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        actor TEXT,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT,
        details_json TEXT NOT NULL
    );""",

"""CREATE TABLE IF NOT EXISTS abuse_log (
    abuse_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    ip_hint TEXT,
    endpoint TEXT NOT NULL,
    reason TEXT NOT NULL,
    meta_json TEXT NOT NULL
);""",
"""CREATE TABLE IF NOT EXISTS lead_intake (
    lead_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    source TEXT,
    page_id TEXT,
    client_id TEXT,
    name TEXT,
    phone TEXT,
    email TEXT,
    message TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    utm_term TEXT,
    utm_content TEXT,
    referrer TEXT,
    user_agent TEXT,
    ip_hint TEXT,
    spam_score INTEGER NOT NULL DEFAULT 0,
    is_spam INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'new',
    booking_status TEXT NOT NULL DEFAULT 'none',
    booking_value REAL,
    booking_currency TEXT,
    booking_ts TEXT,
    telegram_chat_id TEXT,
    meta_json TEXT NOT NULL
);""",
"""CREATE UNIQUE INDEX IF NOT EXISTS idx_lead_intake_telegram_chat_id ON lead_intake(telegram_chat_id) WHERE telegram_chat_id IS NOT NULL;""",

    # payments (v1)
    """CREATE TABLE IF NOT EXISTS payments (
        payment_id TEXT PRIMARY KEY,
        booking_id TEXT NOT NULL,
        lead_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        currency TEXT NOT NULL,
        provider TEXT NOT NULL,
        method TEXT NOT NULL,
        status TEXT NOT NULL,
        external_ref TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        meta_json TEXT NOT NULL,
        FOREIGN KEY(lead_id) REFERENCES lead_intake(lead_id)
    );""",
    """CREATE INDEX IF NOT EXISTS idx_payments_booking ON payments(booking_id, created_at);""",
    """CREATE INDEX IF NOT EXISTS idx_payments_lead ON payments(lead_id, created_at);""",
    """CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status, updated_at);""",


# payment reconciliation (v1)
"""CREATE TABLE IF NOT EXISTS payment_reconciliation (
    payment_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    matched_amount REAL,
    matched_currency TEXT,
    matched_ref TEXT,
    note TEXT,
    updated_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    FOREIGN KEY(payment_id) REFERENCES payments(payment_id)
);""",
"""CREATE INDEX IF NOT EXISTS idx_payrec_status_time ON payment_reconciliation(status, updated_at);""",
# exports (CRM)
"""CREATE TABLE IF NOT EXISTS export_schemas (
    name TEXT PRIMARY KEY,
    schema_version INTEGER NOT NULL,
    schema_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);""",

"""CREATE TABLE IF NOT EXISTS export_presets (
  name TEXT PRIMARY KEY,
  preset_version INTEGER NOT NULL,
  schema_name TEXT NOT NULL,
  format TEXT NOT NULL,
  delimiter TEXT,
  sheet_name TEXT,
  date_format TEXT,
  locale TEXT,
  header_map_json TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  updated_at TEXT NOT NULL
);""",
"""CREATE TABLE IF NOT EXISTS export_jobs (
  job_id TEXT PRIMARY KEY,
  preset_name TEXT NOT NULL,
  cron TEXT NOT NULL,
  target TEXT NOT NULL,
  output_dir TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  last_run TEXT,
  next_run TEXT,
  fail_count INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(preset_name) REFERENCES export_presets(name)
);""",
"""CREATE INDEX IF NOT EXISTS idx_export_jobs_due ON export_jobs(enabled, next_run);""",
"""CREATE INDEX IF NOT EXISTS idx_export_jobs_time ON export_jobs(updated_at);""",
"""CREATE INDEX IF NOT EXISTS idx_export_presets_time ON export_presets(updated_at);""",
"""CREATE INDEX IF NOT EXISTS idx_export_schemas_time ON export_schemas(updated_at);""",


"""CREATE TABLE IF NOT EXISTS ad_spend_daily (
    spend_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    day TEXT NOT NULL,
    source TEXT NOT NULL,
    utm_campaign TEXT,
    client_id TEXT,
    spend_value REAL NOT NULL,
    spend_currency TEXT NOT NULL DEFAULT 'THB',
    meta_json TEXT NOT NULL
);""",

"""CREATE TABLE IF NOT EXISTS alert_thresholds (
    k TEXT PRIMARY KEY,
    v TEXT NOT NULL
);""",
"""CREATE TABLE IF NOT EXISTS alerts_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    status TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    campaign TEXT,
    metric TEXT,
    value REAL,
    threshold REAL,
    message TEXT,
    ack_ts TEXT,
    ack_by TEXT,
    resolved_ts TEXT,
    note TEXT
);""",

"""CREATE TABLE IF NOT EXISTS notify_config (
    k TEXT PRIMARY KEY,
    v TEXT NOT NULL
);""",
"""CREATE TABLE IF NOT EXISTS notify_dedupe (
    fingerprint TEXT PRIMARY KEY,
    last_sent_ts TEXT NOT NULL
);""",


# auth (console)
"""CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    pw_hash TEXT NOT NULL,
    role TEXT NOT NULL,              -- admin | operator | viewer
    is_active INTEGER NOT NULL DEFAULT 1,
    created_ts TEXT NOT NULL,
    updated_ts TEXT NOT NULL
);""",
"""CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_ts TEXT NOT NULL,
    expires_ts TEXT NOT NULL,
    last_seen_ts TEXT NOT NULL,
    ip_hint TEXT,
    user_agent TEXT,
    is_revoked INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);""",


# hook retry queue (reliability)
"""CREATE TABLE IF NOT EXISTS hook_retries (
    retry_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    hook_name TEXT NOT NULL,
    topic TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    max_attempts INTEGER NOT NULL,
    status TEXT NOT NULL,
    next_attempt_at TEXT NOT NULL,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(event_id) REFERENCES op_events(event_id)
);""",
"""CREATE INDEX IF NOT EXISTS idx_hook_retries_status_time ON hook_retries(status, next_attempt_at);""",
"""CREATE INDEX IF NOT EXISTS idx_hook_retries_event_hook ON hook_retries(event_id, hook_name);""",


    # reliability: integrity reports
    """CREATE TABLE IF NOT EXISTS integrity_reports (
        report_id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL,
        issues_json TEXT NOT NULL
    );""",
    """CREATE INDEX IF NOT EXISTS idx_integrity_reports_created ON integrity_reports (created_at DESC);""",

    # --- Money Board v2 / CRM ---

    """CREATE TABLE IF NOT EXISTS customers (
        customer_id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        display_name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        telegram_id TEXT,
        telegram_username TEXT,
        line_id TEXT,
        whatsapp_id TEXT,
        language_pref TEXT DEFAULT 'en',
        notes TEXT,
        tags_json TEXT NOT NULL DEFAULT '[]',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(client_id) REFERENCES clients(client_id)
    );""",
    """CREATE INDEX IF NOT EXISTS idx_customers_client ON customers(client_id);""",
    """CREATE INDEX IF NOT EXISTS idx_customers_telegram ON customers(telegram_id);""",
    """CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);""",

    """CREATE TABLE IF NOT EXISTS bookings (
        booking_id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        lead_id INTEGER,
        
        channel TEXT NOT NULL,
        status TEXT NOT NULL,
        status_reason TEXT,
        
        package_id TEXT NOT NULL,
        package_name_snapshot TEXT NOT NULL,
        price_amount REAL NOT NULL,
        currency TEXT NOT NULL,
        duration_minutes INTEGER NOT NULL,
        addons_json TEXT NOT NULL DEFAULT '[]',
        quantity INTEGER NOT NULL DEFAULT 1,
        
        preferred_time_window TEXT,
        preferred_date TEXT,
        final_slot_start TEXT,
        final_slot_end TEXT,
        
        deposit_required INTEGER NOT NULL DEFAULT 0,
        deposit_amount REAL DEFAULT 0,
        deposit_status TEXT NOT NULL DEFAULT 'none',
        payment_link TEXT,
        payment_ref TEXT,
        
        tags_json TEXT NOT NULL DEFAULT '[]',
        notes_internal TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        
        FOREIGN KEY(client_id) REFERENCES clients(client_id),
        FOREIGN KEY(customer_id) REFERENCES customers(customer_id),
        FOREIGN KEY(package_id) REFERENCES service_packages(package_id)
    );""",
    """CREATE INDEX IF NOT EXISTS idx_bookings_client_status ON bookings(client_id, status);""",
    """CREATE INDEX IF NOT EXISTS idx_bookings_customer ON bookings(customer_id);""",
    """CREATE INDEX IF NOT EXISTS idx_bookings_created ON bookings(created_at);""",

    """CREATE TABLE IF NOT EXISTS booking_events (
        event_id TEXT PRIMARY KEY,
        booking_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        event_type TEXT NOT NULL,
        actor_type TEXT NOT NULL,
        actor_id TEXT,
        diff_payload TEXT NOT NULL, -- JSON
        meta_json TEXT NOT NULL DEFAULT '{}',
        FOREIGN KEY(booking_id) REFERENCES bookings(booking_id)
    );""",
    """CREATE INDEX IF NOT EXISTS idx_booking_events_booking ON booking_events(booking_id, timestamp);""",
]

def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    try:
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA synchronous=NORMAL;")
        con.execute("PRAGMA busy_timeout=3000;")
    except Exception:
        pass
    con.row_factory = sqlite3.Row
    return con


class Transaction:
    """Context manager for database transactions with automatic rollback on error."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.con = None
        self._committed = False
    
    def __enter__(self):
        self.con = connect(self.db_path)
        self.con.execute("BEGIN")
        return self.con
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Error occurred, rollback
            try:
                self.con.rollback()
            except Exception:
                pass
        elif not self._committed:
            # No error but not explicitly committed, commit
            try:
                self.con.commit()
            except Exception:
                pass
        try:
            self.con.close()
        except Exception:
            pass
        return False  # Don't suppress exceptions
    
    def commit(self):
        """Explicitly commit the transaction."""
        if self.con and not self._committed:
            self.con.commit()
            self._committed = True
    
    def rollback(self):
        """Explicitly rollback the transaction."""
        if self.con and not self._committed:
            self.con.rollback()
            self._committed = True


def apply_migrations(conn) -> None:
    """Best-effort migrations for evolving schema."""
    cur = conn.cursor()

    def _col_exists(table: str, col: str) -> bool:
        rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
        return any(r[1] == col for r in rows)

    # lead_intake: booking + value fields
    try:
        if _col_exists("lead_intake", "lead_id"):
            if not _col_exists("lead_intake", "status"):
                cur.execute("ALTER TABLE lead_intake ADD COLUMN status TEXT NOT NULL DEFAULT 'new'")
            if not _col_exists("lead_intake", "booking_status"):
                cur.execute("ALTER TABLE lead_intake ADD COLUMN booking_status TEXT NOT NULL DEFAULT 'none'")
            if not _col_exists("lead_intake", "booking_value"):
                cur.execute("ALTER TABLE lead_intake ADD COLUMN booking_value REAL")
            if not _col_exists("lead_intake", "booking_currency"):
                cur.execute("ALTER TABLE lead_intake ADD COLUMN booking_currency TEXT")
            if not _col_exists("lead_intake", "booking_ts"):
                cur.execute("ALTER TABLE lead_intake ADD COLUMN booking_ts TEXT")
            # Add telegram_chat_id column for efficient Telegram bot lookups
            if not _col_exists("lead_intake", "telegram_chat_id"):
                cur.execute("ALTER TABLE lead_intake ADD COLUMN telegram_chat_id TEXT")
                # Create unique index for telegram_chat_id
                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_lead_intake_telegram_chat_id ON lead_intake(telegram_chat_id) WHERE telegram_chat_id IS NOT NULL")
                # Migrate existing leads: extract telegram_chat_id from meta_json
                cur.execute("""
                    UPDATE lead_intake 
                    SET telegram_chat_id = json_extract(meta_json, '$.telegram_chat_id')
                    WHERE telegram_chat_id IS NULL 
                    AND json_extract(meta_json, '$.telegram_chat_id') IS NOT NULL
                """)
    except Exception:
        pass

    # op_events: operational event bus (best-effort for existing DBs)
    try:
        cur.execute("""CREATE TABLE IF NOT EXISTS op_events (
            event_id TEXT PRIMARY KEY,
            occurred_at TEXT NOT NULL,
            topic TEXT NOT NULL,
            schema_version INTEGER NOT NULL,
            aggregate_type TEXT NOT NULL,
            aggregate_id TEXT NOT NULL,
            actor TEXT,
            correlation_id TEXT,
            causation_id TEXT,
            payload_json TEXT NOT NULL
        );""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_op_events_agg_time ON op_events(aggregate_type, aggregate_id, occurred_at);""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_op_events_topic_time ON op_events(topic, occurred_at);""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_op_events_corr_time ON op_events(correlation_id, occurred_at);""")
    except Exception:
        pass

    # op_states: operational materialized state (best-effort for existing DBs)
    try:
        cur.execute("""CREATE TABLE IF NOT EXISTS op_states (
            aggregate_type TEXT NOT NULL,
            aggregate_id TEXT NOT NULL,
            state TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_event_id TEXT,
            last_topic TEXT,
            last_occurred_at TEXT,
            PRIMARY KEY (aggregate_type, aggregate_id)
        );""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_op_states_state ON op_states(aggregate_type, state, updated_at);""")
    except Exception:
        pass

    # policy_audit_logs: governance receipts (best-effort)
    try:
        cur.execute("""CREATE TABLE IF NOT EXISTS policy_audit_logs (
            audit_id TEXT PRIMARY KEY,
            ts TEXT NOT NULL,
            policy TEXT NOT NULL,
            decision TEXT NOT NULL,
            subject_type TEXT,
            subject_id TEXT,
            topic TEXT,
            schema_version INTEGER,
            reason TEXT,
            meta_json TEXT NOT NULL
        );""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_policy_audit_time ON policy_audit_logs(ts);""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_policy_audit_policy ON policy_audit_logs(policy, decision, ts);""")
    except Exception:
        pass

    # chat_channels: registry (best-effort)
    try:
        cur.execute("""CREATE TABLE IF NOT EXISTS chat_channels (
            channel_id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            handle TEXT NOT NULL,
            display_name TEXT,
            meta_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_chat_channels_provider_handle ON chat_channels(provider, handle);""")
    except Exception:
        pass




    # alerts (best-effort)
    try:
        cur.execute("""CREATE TABLE IF NOT EXISTS alert_thresholds (
            k TEXT PRIMARY KEY,
            v TEXT NOT NULL
        );""")
        cur.execute("""CREATE TABLE IF NOT EXISTS alerts_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            status TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            campaign TEXT,
            metric TEXT,
            value REAL,
            threshold REAL,
            message TEXT
        );""")
    except Exception:
        pass


    # sessions: csrf_token for CSRF validation
    try:
        if _col_exists("sessions", "session_id") and not _col_exists("sessions", "csrf_token"):
            cur.execute("ALTER TABLE sessions ADD COLUMN csrf_token TEXT")
    except Exception:
        pass

    # sessions: tenant_id for session-scoped tenant verification (S2)
    try:
        if _col_exists("sessions", "session_id") and not _col_exists("sessions", "tenant_id"):
            cur.execute("ALTER TABLE sessions ADD COLUMN tenant_id TEXT")
    except Exception:
        pass

    # api_keys: optional table for Phase S3 tenant-scoped API keys
    try:
        cur.execute("""CREATE TABLE IF NOT EXISTS api_keys (
            key_hash TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
        );""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id);""")
    except Exception:
        pass

    # notifier tables (best-effort)
    try:
        cur.execute("""CREATE TABLE IF NOT EXISTS notify_config (
            k TEXT PRIMARY KEY,
            v TEXT NOT NULL
        );""")
        cur.execute("""CREATE TABLE IF NOT EXISTS notify_dedupe (
            fingerprint TEXT PRIMARY KEY,
            last_sent_ts TEXT NOT NULL
        );""")
    except Exception:
        pass

    # alerts_log lifecycle columns
    try:
        if _col_exists("alerts_log", "id"):
            if not _col_exists("alerts_log", "ack_ts"):
                cur.execute("ALTER TABLE alerts_log ADD COLUMN ack_ts TEXT")
            if not _col_exists("alerts_log", "ack_by"):
                cur.execute("ALTER TABLE alerts_log ADD COLUMN ack_by TEXT")
            if not _col_exists("alerts_log", "resolved_ts"):
                cur.execute("ALTER TABLE alerts_log ADD COLUMN resolved_ts TEXT")
            if not _col_exists("alerts_log", "note"):
                cur.execute("ALTER TABLE alerts_log ADD COLUMN note TEXT")
    except Exception:
        pass

    # Money Board v2 Migrations (best-effort)
    try:
        # Customers
        cur.execute("""CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            display_name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            telegram_id TEXT,
            telegram_username TEXT,
            line_id TEXT,
            whatsapp_id TEXT,
            language_pref TEXT DEFAULT 'en',
            notes TEXT,
            tags_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(client_id) REFERENCES clients(client_id)
        );""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_customers_client ON customers(client_id);""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_customers_telegram ON customers(telegram_id);""")

        # Bookings
        cur.execute("""CREATE TABLE IF NOT EXISTS bookings (
            booking_id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            lead_id INTEGER,
            channel TEXT NOT NULL,
            status TEXT NOT NULL,
            status_reason TEXT,
            package_id TEXT NOT NULL,
            package_name_snapshot TEXT NOT NULL,
            price_amount REAL NOT NULL,
            currency TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            addons_json TEXT NOT NULL DEFAULT '[]',
            quantity INTEGER NOT NULL DEFAULT 1,
            preferred_time_window TEXT,
            preferred_date TEXT,
            final_slot_start TEXT,
            final_slot_end TEXT,
            deposit_required INTEGER NOT NULL DEFAULT 0,
            deposit_amount REAL DEFAULT 0,
            deposit_status TEXT NOT NULL DEFAULT 'none',
            payment_link TEXT,
            payment_ref TEXT,
            tags_json TEXT NOT NULL DEFAULT '[]',
            notes_internal TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(client_id) REFERENCES clients(client_id),
            FOREIGN KEY(customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY(package_id) REFERENCES service_packages(package_id)
        );""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_bookings_client_status ON bookings(client_id, status);""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_bookings_customer ON bookings(customer_id);""")

        # Booking Events
        cur.execute("""CREATE TABLE IF NOT EXISTS booking_events (
            event_id TEXT PRIMARY KEY,
            booking_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            actor_type TEXT NOT NULL,
            actor_id TEXT,
            diff_payload TEXT NOT NULL,
            meta_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(booking_id) REFERENCES bookings(booking_id)
        );""")
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_booking_events_booking ON booking_events(booking_id, timestamp);""")

    except Exception as e:
        # Just print locally, don't crash migration
        print(f"[Migration] Error creating Money Board v2 tables: {e}")

def init_db(db_path: str) -> None:
    con = connect(db_path)
    try:
        cur = con.cursor()
        for stmt in SCHEMA_SQL:
            try:
                cur.execute(stmt)
            except Exception:
                pass
        con.commit()
        # Apply migrations after basic schema
        apply_migrations(con)
    finally:
        con.close()

def execute(con: sqlite3.Connection, sql: str, params: Tuple[Any, ...] = ()) -> None:
    con.execute(sql, params)

def fetchone(con: sqlite3.Connection, sql: str, params: Tuple[Any, ...] = ()) -> Optional[sqlite3.Row]:
    cur = con.execute(sql, params)
    return cur.fetchone()

def fetchall(con: sqlite3.Connection, sql: str, params: Tuple[Any, ...] = ()) -> List[sqlite3.Row]:
    cur = con.execute(sql, params)
    return cur.fetchall()
