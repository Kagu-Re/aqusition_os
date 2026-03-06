from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from .console_support import require_role
from .timeline_engine import project_timeline


router = APIRouter()


@router.get("/api/timeline")
def get_timeline(
    db: str,
    aggregate_type: Optional[str] = None,
    aggregate_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    limit: int = 200,
    _: None = Depends(require_role("viewer")),
):
    items = project_timeline(
        db,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        correlation_id=correlation_id,
        limit=limit,
    )
    return {"count": len(items), "items": [i.model_dump() for i in items]}
