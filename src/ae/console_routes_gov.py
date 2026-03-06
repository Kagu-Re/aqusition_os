from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from .repo_policy_audit import list_policy_audits


router = APIRouter(prefix="/api/gov", tags=["governance"])


@router.get("/policy-audit")
def get_policy_audit(
    db: str = Query(..., description="Path to SQLite DB"),
    policy: Optional[str] = Query(None),
    decision: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=2000),
):
    items = list_policy_audits(db, policy=policy, decision=decision, limit=limit)
    return {
        "count": len(items),
        "items": [i.model_dump() for i in items],
    }
