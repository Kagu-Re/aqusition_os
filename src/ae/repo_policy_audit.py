from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import TypeAdapter

from . import db
from .models import PolicyAuditLog


_audit_adapter = TypeAdapter(PolicyAuditLog)


def insert_policy_audit(db_path: str, log: PolicyAuditLog) -> None:
    """Append a policy audit record.

    This is used as a governance receipt layer for policy engines.
    """
    con = db.connect(db_path)
    try:
        con.execute(
            """INSERT INTO policy_audit_logs(
                audit_id, ts, policy, decision,
                subject_type, subject_id,
                topic, schema_version,
                reason, meta_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                log.audit_id,
                log.ts.isoformat(),
                log.policy,
                log.decision,
                log.subject_type,
                log.subject_id,
                log.topic,
                log.schema_version,
                log.reason,
                json.dumps(log.meta, ensure_ascii=False),
            ),
        )
        con.commit()
    finally:
        con.close()


def list_policy_audits(
    db_path: str,
    *,
    policy: Optional[str] = None,
    decision: Optional[str] = None,
    limit: int = 200,
) -> List[PolicyAuditLog]:
    con = db.connect(db_path)
    try:
        where = []
        params: List[Any] = []
        if policy:
            where.append("policy=?")
            params.append(policy)
        if decision:
            where.append("decision=?")
            params.append(decision)

        sql = "SELECT * FROM policy_audit_logs"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY ts DESC LIMIT ?"
        params.append(int(max(1, min(limit, 2000))))

        rows = con.execute(sql, tuple(params)).fetchall()
        out: List[PolicyAuditLog] = []
        for r in rows:
            d = dict(r)
            d["ts"] = datetime.fromisoformat(d["ts"])
            d["meta"] = json.loads(d.get("meta_json") or "{}")
            d.pop("meta_json", None)
            out.append(_audit_adapter.validate_python(d))
        return out
    finally:
        con.close()
