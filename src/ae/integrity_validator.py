from __future__ import annotations

import json
import sqlite3
from typing import List, Dict, Any
from datetime import datetime, timezone
import uuid

from .db import connect
from .models import IntegrityIssue, IntegrityReport
from .repo_integrity_reports import insert_integrity_report
from .event_bus import EventBus


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _table_exists(con: sqlite3.Connection, name: str) -> bool:
    row = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return bool(row)


def run_integrity_check(db_path: str, *, emit_events: bool = True) -> IntegrityReport:
    con = connect(db_path)
    issues: List[IntegrityIssue] = []

    # 1) Validate op_events payload JSON
    if _table_exists(con, "op_events"):
        for (event_id, payload_json) in con.execute("SELECT event_id, payload_json FROM op_events").fetchall():
            try:
                json.loads(payload_json or "{}")
            except Exception as e:
                issues.append(
                    IntegrityIssue(
                        code="op_events.payload_json_invalid",
                        severity="error",
                        message=f"Invalid payload_json for op_event {event_id}: {e}",
                        entity_type="op_event",
                        entity_id=event_id,
                    )
                )

    # 2) op_states pointers must resolve
    if _table_exists(con, "op_states") and _table_exists(con, "op_events"):
        rows = con.execute(
            """SELECT aggregate_type, aggregate_id, state, last_event_id, last_topic, last_occurred_at
               FROM op_states"""
        ).fetchall()
        for agg_type, agg_id, state, last_event_id, last_topic, last_occurred_at in rows:
            if not last_event_id:
                issues.append(
                    IntegrityIssue(
                        code="op_states.missing_last_event",
                        severity="warning",
                        message="op_state has no last_event_id",
                        entity_type="op_state",
                        entity_id=f"{agg_type}:{agg_id}",
                        meta={"state": state},
                    )
                )
                continue
            ev = con.execute(
                "SELECT topic, occurred_at FROM op_events WHERE event_id = ?",
                (last_event_id,),
            ).fetchone()
            if not ev:
                issues.append(
                    IntegrityIssue(
                        code="op_states.last_event_missing",
                        severity="error",
                        message="op_state.last_event_id not found in op_events",
                        entity_type="op_state",
                        entity_id=f"{agg_type}:{agg_id}",
                        meta={"last_event_id": last_event_id},
                    )
                )
                continue
            topic, occurred_at = ev
            if last_topic and topic != last_topic:
                issues.append(
                    IntegrityIssue(
                        code="op_states.last_topic_mismatch",
                        severity="error",
                        message="op_state.last_topic does not match op_events.topic",
                        entity_type="op_state",
                        entity_id=f"{agg_type}:{agg_id}",
                        meta={"last_topic": last_topic, "event_topic": topic, "event_id": last_event_id},
                    )
                )
            if last_occurred_at and occurred_at != last_occurred_at:
                issues.append(
                    IntegrityIssue(
                        code="op_states.last_occurred_at_mismatch",
                        severity="warning",
                        message="op_state.last_occurred_at does not match op_events.occurred_at",
                        entity_type="op_state",
                        entity_id=f"{agg_type}:{agg_id}",
                        meta={"last_occurred_at": last_occurred_at, "event_occurred_at": occurred_at, "event_id": last_event_id},
                    )
                )

    # 3) Payment referential integrity
    if _table_exists(con, "payments") and _table_exists(con, "lead_intake"):
        rows = con.execute("SELECT payment_id, lead_id, booking_id, amount, currency, status FROM payments").fetchall()
        for payment_id, lead_id, booking_id, amount, currency, status in rows:
            lead = con.execute("SELECT lead_id FROM lead_intake WHERE lead_id = ?", (lead_id,)).fetchone()
            if not lead:
                issues.append(
                    IntegrityIssue(
                        code="payments.orphan_lead",
                        severity="error",
                        message="Payment references missing lead",
                        entity_type="payment",
                        entity_id=payment_id,
                        meta={"lead_id": lead_id},
                    )
                )
            expected_booking = f"lead-{lead_id}"
            if booking_id and booking_id != expected_booking:
                issues.append(
                    IntegrityIssue(
                        code="payments.booking_id_mismatch",
                        severity="error",
                        message="Payment booking_id does not match expected lead binding",
                        entity_type="payment",
                        entity_id=payment_id,
                        meta={"booking_id": booking_id, "expected": expected_booking, "lead_id": lead_id},
                    )
                )

    # 4) Chat conversation lead binding
    if _table_exists(con, "chat_conversations") and _table_exists(con, "lead_intake"):
        rows = con.execute("SELECT conversation_id, lead_id FROM chat_conversations WHERE lead_id IS NOT NULL AND lead_id != ''").fetchall()
        for conversation_id, lead_id in rows:
            lead = con.execute("SELECT lead_id FROM lead_intake WHERE lead_id = ?", (lead_id,)).fetchone()
            if not lead:
                issues.append(
                    IntegrityIssue(
                        code="chat_conversations.orphan_lead",
                        severity="warning",
                        message="Chat conversation references missing lead",
                        entity_type="chat_conversation",
                        entity_id=conversation_id,
                        meta={"lead_id": lead_id},
                    )
                )

    # 5) QR attribution menu binding
    if _table_exists(con, "qr_attributions") and _table_exists(con, "menus"):
        rows = con.execute("SELECT attribution_id, menu_id FROM qr_attributions WHERE menu_id IS NOT NULL AND menu_id != ''").fetchall()
        for attribution_id, menu_id in rows:
            menu = con.execute("SELECT menu_id FROM menus WHERE menu_id = ?", (menu_id,)).fetchone()
            if not menu:
                issues.append(
                    IntegrityIssue(
                        code="qr_attributions.orphan_menu",
                        severity="warning",
                        message="QR attribution references missing menu",
                        entity_type="qr_attribution",
                        entity_id=attribution_id,
                        meta={"menu_id": menu_id},
                    )
                )

    # 6) Event-to-lead consistency (events with page_id should ideally have corresponding leads)
    if _table_exists(con, "events") and _table_exists(con, "lead_intake"):
        # Find pages with events but no leads (informational, not an error)
        pages_with_events = con.execute("""
            SELECT DISTINCT page_id 
            FROM events 
            WHERE page_id IS NOT NULL AND page_id != ''
        """).fetchall()
        
        pages_with_leads = con.execute("""
            SELECT DISTINCT page_id 
            FROM lead_intake 
            WHERE page_id IS NOT NULL AND page_id != ''
        """).fetchall()
        
        pages_with_leads_set = {p[0] for p in pages_with_leads}
        pages_with_events_no_leads = [p[0] for p in pages_with_events if p[0] not in pages_with_leads_set]
        
        if pages_with_events_no_leads:
            # This is informational, not an error (pages can have events without leads)
            issues.append(
                IntegrityIssue(
                    code="events.pages_without_leads",
                    severity="info",
                    message=f"Found {len(pages_with_events_no_leads)} pages with events but no leads (may be normal)",
                    entity_type="page",
                    entity_id=None,
                    meta={"page_count": len(pages_with_events_no_leads), "examples": pages_with_events_no_leads[:5]},
                )
            )

    # 7) UTM parameter consistency across events, leads, ad_stats
    if _table_exists(con, "events") and _table_exists(con, "lead_intake"):
        # Check for events and leads with same page_id but different UTM parameters
        # This is a complex check - for now, we'll just note if UTM params exist
        events_with_utm = con.execute("""
            SELECT COUNT(*) 
            FROM events 
            WHERE params_json LIKE '%utm_source%' OR params_json LIKE '%utm_campaign%'
        """).fetchone()[0] or 0
        
        if events_with_utm > 0:
            # Check if leads have matching UTM params (basic check)
            leads_with_utm = con.execute("""
                SELECT COUNT(*) 
                FROM lead_intake 
                WHERE meta_json LIKE '%utm_source%' OR meta_json LIKE '%utm_campaign%'
            """).fetchone()[0] or 0
            
            if events_with_utm > 0 and leads_with_utm == 0:
                issues.append(
                    IntegrityIssue(
                        code="utm.leads_missing_utm",
                        severity="info",
                        message=f"Found {events_with_utm} events with UTM params but {leads_with_utm} leads with UTM params (attribution may be incomplete)",
                        entity_type="system",
                        entity_id=None,
                        meta={"events_with_utm": events_with_utm, "leads_with_utm": leads_with_utm},
                    )
                )

    # 8) Timeline consistency (op_events timestamps align with op_states)
    if _table_exists(con, "op_states") and _table_exists(con, "op_events"):
        timeline_mismatches = con.execute("""
            SELECT os.aggregate_type, os.aggregate_id, os.last_event_id, os.last_occurred_at, oe.occurred_at
            FROM op_states os
            JOIN op_events oe ON os.last_event_id = oe.event_id
            WHERE os.last_occurred_at != oe.occurred_at
        """).fetchall()
        
        if timeline_mismatches:
            for agg_type, agg_id, event_id, state_time, event_time in timeline_mismatches[:10]:  # Limit to first 10
                issues.append(
                    IntegrityIssue(
                        code="timeline.timestamp_mismatch",
                        severity="warning",
                        message=f"Timeline timestamp mismatch for {agg_type}:{agg_id}",
                        entity_type=agg_type,
                        entity_id=agg_id,
                        meta={
                            "event_id": event_id,
                            "state_timestamp": state_time,
                            "event_timestamp": event_time,
                        },
                    )
                )

    # 9) Client-page-template consistency
    if _table_exists(con, "pages") and _table_exists(con, "clients") and _table_exists(con, "templates"):
        inconsistent_pages = con.execute("""
            SELECT p.page_id, p.client_id, p.template_id
            FROM pages p
            LEFT JOIN clients c ON p.client_id = c.client_id
            LEFT JOIN templates t ON p.template_id = t.template_id
            WHERE c.client_id IS NULL OR t.template_id IS NULL
        """).fetchall()
        
        if inconsistent_pages:
            for page_id, client_id, template_id in inconsistent_pages:
                if client_id and not template_id:
                    issues.append(
                        IntegrityIssue(
                            code="pages.invalid_template",
                            severity="error",
                            message=f"Page references invalid template",
                            entity_type="page",
                            entity_id=page_id,
                            meta={"client_id": client_id, "template_id": template_id},
                        )
                    )
                elif template_id and not client_id:
                    issues.append(
                        IntegrityIssue(
                            code="pages.invalid_client",
                            severity="error",
                            message=f"Page references invalid client",
                            entity_type="page",
                            entity_id=page_id,
                            meta={"client_id": client_id, "template_id": template_id},
                        )
                    )

    status = "ok" if not issues else "issues"
    report = insert_integrity_report(db_path, status=status, issues=issues)

    if emit_events:
        # Emit receipt events (best-effort; do not fail integrity run)
        try:
            EventBus.emit_topic(
                db_path,
                topic="op.rel.integrity.checked",
                aggregate_type="system",
                aggregate_id="integrity",
                payload={"report_id": report.report_id, "status": report.status, "issue_count": len(report.issues)},
            )
            if report.status != "ok":
                EventBus.emit_topic(
                    db_path,
                    topic="op.rel.integrity.failed",
                    aggregate_type="system",
                    aggregate_id="integrity",
                    payload={"report_id": report.report_id, "issue_count": len(report.issues)},
                )
        except Exception:
            pass

    return report
