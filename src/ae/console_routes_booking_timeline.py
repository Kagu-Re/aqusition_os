from __future__ import annotations

from fastapi import APIRouter, Depends

from .console_support import require_role
from .timeline_engine import project_timeline


router = APIRouter()


@router.get("/api/bookings/{lead_id}/timeline")
def booking_timeline(
    lead_id: int,
    db: str,
    limit: int = 200,
    _: None = Depends(require_role("viewer")),
):
    """Convenience endpoint: booking timeline mapped from correlation stream.

    OP-BOOK-002B: Booking → Timeline Mapping.
    In v1, a booking is correlated to a lead via `correlation_id = f"lead:{lead_id}"`.
    This endpoint projects the correlated operational stream into timeline items.
    """

    corr = f"lead:{int(lead_id)}"
    items = project_timeline(
        db,
        correlation_id=corr,
        limit=limit,
    )
    return {
        "lead_id": int(lead_id),
        "correlation_id": corr,
        "count": len(items),
        "items": [i.model_dump() for i in items],
    }
