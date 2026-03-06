from __future__ import annotations

import json
import sqlite3
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from .models import IntegrityReport, IntegrityIssue
from .db import connect


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def insert_integrity_report(db_path: str, status: str, issues: List[IntegrityIssue]) -> IntegrityReport:
    report = IntegrityReport(
        report_id=str(uuid.uuid4()),
        created_at=_utc_now_iso(),
        status=status,
        issues=issues,
    )
    con = connect(db_path)
    with con:
        con.execute(
            """INSERT INTO integrity_reports (report_id, created_at, status, issues_json)
               VALUES (?, ?, ?, ?)""",
            (report.report_id, report.created_at, report.status, json.dumps([i.model_dump() for i in issues])),
        )
    return report


def get_integrity_report(db_path: str, report_id: str) -> Optional[IntegrityReport]:
    con = connect(db_path)
    row = con.execute(
        """SELECT report_id, created_at, status, issues_json
           FROM integrity_reports WHERE report_id = ?""",
        (report_id,),
    ).fetchone()
    if not row:
        return None
    issues = [IntegrityIssue(**x) for x in json.loads(row[3] or "[]")]
    return IntegrityReport(report_id=row[0], created_at=row[1], status=row[2], issues=issues)


def get_latest_integrity_report(db_path: str) -> Optional[IntegrityReport]:
    con = connect(db_path)
    row = con.execute(
        """SELECT report_id, created_at, status, issues_json
           FROM integrity_reports ORDER BY created_at DESC LIMIT 1"""
    ).fetchone()
    if not row:
        return None
    issues = [IntegrityIssue(**x) for x in json.loads(row[3] or "[]")]
    return IntegrityReport(report_id=row[0], created_at=row[1], status=row[2], issues=issues)
