from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from .models import OpEvent, PolicyAuditLog
from .repo_policy_audit import insert_policy_audit


def audit_policy_deny(
    db_path: str,
    *,
    policy: str,
    reason: str,
    subject_type: Optional[str] = None,
    subject_id: Optional[str] = None,
    event: Optional[OpEvent] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    """Best-effort append-only governance receipt when a policy denies an action."""
    try:
        log = PolicyAuditLog(
            audit_id=str(uuid.uuid4()),
            ts=datetime.utcnow(),
            policy=policy,
            decision="deny",
            subject_type=subject_type,
            subject_id=subject_id,
            topic=getattr(event, "topic", None),
            schema_version=getattr(event, "schema_version", None),
            reason=reason[:500],
            meta=meta or {},
        )
        insert_policy_audit(db_path, log)
    except Exception:
        return
