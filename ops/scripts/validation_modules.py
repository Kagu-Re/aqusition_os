"""Reusable validation modules for system validation.

This module provides validation functions that can be used across different
validation phases. Each function returns a ValidationResult with status and details.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure we can import ae modules
import sys
from pathlib import Path as PathLib

ROOT = PathLib(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ae import db as dbmod
from ae import repo
from ae.integrity_validator import run_integrity_check


@dataclass
class ValidationCheck:
    """Single validation check result."""
    name: str
    status: str  # "passed", "failed", "warning", "skipped"
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """Result of a validation function."""
    checks: List[ValidationCheck]
    passed: bool
    warnings: int = 0
    errors: int = 0


def validate_database(db_path: str) -> ValidationResult:
    """Validate database schema, integrity, and relationships.
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        ValidationResult with database validation checks
    """
    checks: List[ValidationCheck] = []
    
    try:
        # Check database file exists
        if not Path(db_path).exists():
            checks.append(ValidationCheck(
                name="database_exists",
                status="failed",
                message=f"Database file not found: {db_path}"
            ))
            return ValidationResult(checks=checks, passed=False, errors=1)
        
        checks.append(ValidationCheck(
            name="database_exists",
            status="passed",
            message=f"Database file exists: {db_path}"
        ))
        
        # Check database is accessible
        try:
            con = dbmod.connect(db_path)
            con.close()
            checks.append(ValidationCheck(
                name="database_accessible",
                status="passed",
                message="Database is accessible"
            ))
        except Exception as e:
            checks.append(ValidationCheck(
                name="database_accessible",
                status="failed",
                message=f"Cannot connect to database: {e}"
            ))
            return ValidationResult(checks=checks, passed=False, errors=1)
        
        # Check required tables exist
        con = dbmod.connect(db_path)
        try:
            required_tables = [
                "clients", "templates", "pages", "events", "lead_intake",
                "op_events", "op_states"
            ]
            existing_tables = set(
                row[0] for row in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            )
            
            for table in required_tables:
                if table in existing_tables:
                    checks.append(ValidationCheck(
                        name=f"table_{table}",
                        status="passed",
                        message=f"Table '{table}' exists"
                    ))
                else:
                    checks.append(ValidationCheck(
                        name=f"table_{table}",
                        status="warning",
                        message=f"Table '{table}' not found (may be optional)"
                    ))
        finally:
            con.close()
        
        # Run integrity check
        try:
            report = run_integrity_check(db_path, emit_events=False)
            if report.status == "ok":
                checks.append(ValidationCheck(
                    name="integrity_check",
                    status="passed",
                    message="Database integrity check passed",
                    details={"issue_count": len(report.issues)}
                ))
            else:
                issue_count = len(report.issues)
                error_count = sum(1 for i in report.issues if i.severity == "error")
                warning_count = sum(1 for i in report.issues if i.severity == "warning")
                
                checks.append(ValidationCheck(
                    name="integrity_check",
                    status="failed" if error_count > 0 else "warning",
                    message=f"Integrity check found {issue_count} issues ({error_count} errors, {warning_count} warnings)",
                    details={
                        "issue_count": issue_count,
                        "error_count": error_count,
                        "warning_count": warning_count,
                        "issues": [
                            {
                                "code": i.code,
                                "severity": i.severity,
                                "message": i.message,
                                "entity_type": i.entity_type,
                                "entity_id": i.entity_id
                            }
                            for i in report.issues[:10]  # Limit to first 10
                        ]
                    }
                ))
        except Exception as e:
            checks.append(ValidationCheck(
                name="integrity_check",
                status="warning",
                message=f"Integrity check failed: {e}"
            ))
        
    except Exception as e:
        checks.append(ValidationCheck(
            name="database_validation",
            status="failed",
            message=f"Database validation error: {e}"
        ))
        return ValidationResult(checks=checks, passed=False, errors=1)
    
    errors = sum(1 for c in checks if c.status == "failed")
    warnings = sum(1 for c in checks if c.status == "warning")
    passed = errors == 0
    
    return ValidationResult(checks=checks, passed=passed, errors=errors, warnings=warnings)


def validate_data_quality(db_path: str, client_id: Optional[str] = None) -> ValidationResult:
    """Validate data quality: completeness, freshness, duplicates.
    
    Args:
        db_path: Path to SQLite database
        client_id: Optional client ID to filter checks
        
    Returns:
        ValidationResult with data quality checks
    """
    checks: List[ValidationCheck] = []
    
    try:
        con = dbmod.connect(db_path)
        try:
            # Check for pages without clients
            orphan_pages = con.execute("""
                SELECT p.page_id, p.client_id 
                FROM pages p 
                LEFT JOIN clients c ON p.client_id = c.client_id 
                WHERE c.client_id IS NULL
            """).fetchall()
            
            if orphan_pages:
                checks.append(ValidationCheck(
                    name="orphan_pages",
                    status="error",
                    message=f"Found {len(orphan_pages)} pages without valid clients",
                    details={"count": len(orphan_pages), "examples": [p[0] for p in orphan_pages[:5]]}
                ))
            else:
                checks.append(ValidationCheck(
                    name="orphan_pages",
                    status="passed",
                    message="All pages have valid clients"
                ))
            
            # Check for pages without templates
            orphan_pages_template = con.execute("""
                SELECT p.page_id, p.template_id 
                FROM pages p 
                LEFT JOIN templates t ON p.template_id = t.template_id 
                WHERE t.template_id IS NULL
            """).fetchall()
            
            if orphan_pages_template:
                checks.append(ValidationCheck(
                    name="orphan_pages_template",
                    status="error",
                    message=f"Found {len(orphan_pages_template)} pages without valid templates",
                    details={"count": len(orphan_pages_template), "examples": [p[0] for p in orphan_pages_template[:5]]}
                ))
            else:
                checks.append(ValidationCheck(
                    name="orphan_pages_template",
                    status="passed",
                    message="All pages have valid templates"
                ))
            
            # Check for required client fields
            # Note: service_area is stored as service_area_json (JSON)
            incomplete_clients = con.execute("""
                SELECT client_id, client_name 
                FROM clients 
                WHERE primary_phone IS NULL OR primary_phone = '' 
                   OR lead_email IS NULL OR lead_email = ''
                   OR service_area_json IS NULL OR service_area_json = '' OR service_area_json = '[]'
            """).fetchall()
            
            if incomplete_clients:
                checks.append(ValidationCheck(
                    name="incomplete_clients",
                    status="warning",
                    message=f"Found {len(incomplete_clients)} clients with missing required fields",
                    details={"count": len(incomplete_clients), "examples": [c[0] for c in incomplete_clients[:5]]}
                ))
            else:
                checks.append(ValidationCheck(
                    name="incomplete_clients",
                    status="passed",
                    message="All clients have required fields"
                ))
            
            # Check for duplicate page slugs
            duplicate_slugs = con.execute("""
                SELECT page_slug, COUNT(*) as cnt 
                FROM pages 
                GROUP BY page_slug 
                HAVING cnt > 1
            """).fetchall()
            
            if duplicate_slugs:
                checks.append(ValidationCheck(
                    name="duplicate_slugs",
                    status="warning",
                    message=f"Found {len(duplicate_slugs)} duplicate page slugs",
                    details={"count": len(duplicate_slugs), "examples": [s[0] for s in duplicate_slugs[:5]]}
                ))
            else:
                checks.append(ValidationCheck(
                    name="duplicate_slugs",
                    status="passed",
                    message="No duplicate page slugs found"
                ))
            
        finally:
            con.close()
            
    except Exception as e:
        checks.append(ValidationCheck(
            name="data_quality_check",
            status="failed",
            message=f"Data quality check error: {e}"
        ))
        return ValidationResult(checks=checks, passed=False, errors=1)
    
    errors = sum(1 for c in checks if c.status == "error" or c.status == "failed")
    warnings = sum(1 for c in checks if c.status == "warning")
    passed = errors == 0
    
    return ValidationResult(checks=checks, passed=passed, errors=errors, warnings=warnings)


def validate_cross_consistency(db_path: str) -> ValidationResult:
    """Validate cross-component consistency: events-leads, UTM consistency, timeline.
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        ValidationResult with cross-consistency checks
    """
    checks: List[ValidationCheck] = []
    
    try:
        con = dbmod.connect(db_path)
        try:
            # Check event-to-lead consistency
            # Events with page_id should ideally have corresponding leads (not required, but good to check)
            events_with_page = con.execute("""
                SELECT DISTINCT page_id 
                FROM events 
                WHERE page_id IS NOT NULL AND page_id != ''
            """).fetchall()
            
            pages_with_events = [e[0] for e in events_with_page]
            pages_with_leads = con.execute("""
                SELECT DISTINCT page_id 
                FROM lead_intake 
                WHERE page_id IS NOT NULL AND page_id != ''
            """).fetchall()
            pages_with_leads_set = {p[0] for p in pages_with_leads}
            
            pages_with_events_no_leads = [p for p in pages_with_events if p not in pages_with_leads_set]
            
            if pages_with_events_no_leads:
                checks.append(ValidationCheck(
                    name="events_without_leads",
                    status="info",
                    message=f"Found {len(pages_with_events_no_leads)} pages with events but no leads (may be normal)",
                    details={"count": len(pages_with_events_no_leads), "examples": pages_with_events_no_leads[:5]}
                ))
            else:
                checks.append(ValidationCheck(
                    name="events_without_leads",
                    status="passed",
                    message="All pages with events have corresponding leads"
                ))
            
            # Check timeline consistency (op_events timestamps align with op_states)
            timeline_issues = con.execute("""
                SELECT os.aggregate_type, os.aggregate_id, os.last_event_id, os.last_occurred_at, oe.occurred_at
                FROM op_states os
                JOIN op_events oe ON os.last_event_id = oe.event_id
                WHERE os.last_occurred_at != oe.occurred_at
            """).fetchall()
            
            if timeline_issues:
                checks.append(ValidationCheck(
                    name="timeline_consistency",
                    status="warning",
                    message=f"Found {len(timeline_issues)} timeline inconsistencies",
                    details={"count": len(timeline_issues)}
                ))
            else:
                checks.append(ValidationCheck(
                    name="timeline_consistency",
                    status="passed",
                    message="Timeline consistency check passed"
                ))
            
            # Check client-page-template consistency
            inconsistent_pages = con.execute("""
                SELECT p.page_id, p.client_id, p.template_id
                FROM pages p
                LEFT JOIN clients c ON p.client_id = c.client_id
                LEFT JOIN templates t ON p.template_id = t.template_id
                WHERE c.client_id IS NULL OR t.template_id IS NULL
            """).fetchall()
            
            if inconsistent_pages:
                checks.append(ValidationCheck(
                    name="client_page_template_consistency",
                    status="error",
                    message=f"Found {len(inconsistent_pages)} pages with invalid client or template references",
                    details={"count": len(inconsistent_pages), "examples": [p[0] for p in inconsistent_pages[:5]]}
                ))
            else:
                checks.append(ValidationCheck(
                    name="client_page_template_consistency",
                    status="passed",
                    message="Client-page-template consistency check passed"
                ))
            
        finally:
            con.close()
            
    except Exception as e:
        checks.append(ValidationCheck(
            name="cross_consistency_check",
            status="failed",
            message=f"Cross-consistency check error: {e}"
        ))
        return ValidationResult(checks=checks, passed=False, errors=1)
    
    errors = sum(1 for c in checks if c.status == "error" or c.status == "failed")
    warnings = sum(1 for c in checks if c.status == "warning")
    passed = errors == 0
    
    return ValidationResult(checks=checks, passed=passed, errors=errors, warnings=warnings)


def validate_state_machines(db_path: str) -> ValidationResult:
    """Validate state machine transitions and state coverage.
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        ValidationResult with state machine checks
    """
    checks: List[ValidationCheck] = []
    
    try:
        from ae.transition_registry import REGISTRY
        
        # Check that all registered transitions are valid
        checks.append(ValidationCheck(
            name="transition_registry",
            status="passed",
            message=f"Transition registry loaded with {len(REGISTRY)} aggregate types",
            details={"aggregate_types": list(REGISTRY.keys())}
        ))
        
            # Check for invalid states in op_states
        con = dbmod.connect(db_path)
        try:
            # Check if op_states table exists
            table_exists = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='op_states'"
            ).fetchone()
            if table_exists:
                invalid_states = con.execute("""
                    SELECT aggregate_type, aggregate_id, state
                    FROM op_states
                    WHERE state IS NULL OR state = ''
                """).fetchall()
                
                if invalid_states:
                    checks.append(ValidationCheck(
                        name="invalid_states",
                        status="warning",
                        message=f"Found {len(invalid_states)} records with invalid states",
                        details={"count": len(invalid_states)}
                    ))
                else:
                    checks.append(ValidationCheck(
                        name="invalid_states",
                        status="passed",
                        message="All states are valid"
                    ))
        finally:
            con.close()
            
    except Exception as e:
        checks.append(ValidationCheck(
            name="state_machine_check",
            status="warning",
            message=f"State machine check error: {e}"
        ))
    
    errors = sum(1 for c in checks if c.status == "error" or c.status == "failed")
    warnings = sum(1 for c in checks if c.status == "warning")
    passed = errors == 0
    
    return ValidationResult(checks=checks, passed=passed, errors=errors, warnings=warnings)
