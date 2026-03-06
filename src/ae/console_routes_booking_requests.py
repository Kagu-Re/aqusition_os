from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional

from .console_support import require_role, _resolve_db_path
from .tenant import get_scoped_client_id
from . import repo
from .models import BookingRequest
from datetime import datetime

admin_router = APIRouter(prefix="/api/booking-requests", tags=["booking-requests"])

_admin = require_role("operator")


class BookingRequestCreate(BaseModel):
    request_id: str = Field(min_length=1)
    lead_id: int
    package_id: str = Field(min_length=1)
    preferred_window: Optional[str] = None
    location: Optional[str] = None
    status: str = "requested"
    meta_json: dict = Field(default_factory=dict)


class BookingRequestStatusUpdate(BaseModel):
    status: str
    preferred_window: Optional[str] = None
    location: Optional[str] = None


@admin_router.get("")
def list_booking_requests(
    request: Request,
    lead_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    _=Depends(_admin),
):
    """List booking requests with optional filters."""
    scoped = get_scoped_client_id(request)
    effective_client_id = scoped
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    items = repo.list_booking_requests(
        db_path, lead_id=lead_id, status=status, client_id=effective_client_id, limit=limit
    )
    return {"count": len(items), "items": [b.model_dump() for b in items]}


@admin_router.get("/{request_id}")
def get_booking_request(request_id: str, request: Request, _=Depends(_admin)):
    """Get a booking request by ID."""
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    booking = repo.get_booking_request(db_path, request_id)
    if not booking:
        raise HTTPException(status_code=404, detail="booking_request_not_found")
    scoped = get_scoped_client_id(request)
    if scoped:
        br_client = repo.get_booking_request_client_id(db_path, request_id)
        if br_client and br_client != scoped:
            raise HTTPException(status_code=403, detail="forbidden: booking not in tenant scope")
    return {"booking": booking.model_dump()}


@admin_router.post("")
def create_booking_request_endpoint(payload: BookingRequestCreate, request: Request, _=Depends(_admin)):
    """Create a new booking request."""
    scoped = get_scoped_client_id(request)
    if scoped:
        pkg = repo.get_package(_resolve_db_path(request.query_params.get("db"), request), payload.package_id)
        if pkg and pkg.client_id != scoped:
            raise HTTPException(status_code=403, detail="forbidden: package not in tenant scope")
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    now = datetime.utcnow()
    booking = BookingRequest(
        request_id=payload.request_id,
        lead_id=payload.lead_id,
        package_id=payload.package_id,
        preferred_window=payload.preferred_window,
        location=payload.location,
        status=payload.status,
        meta_json=payload.meta_json or {},
        created_at=now,
        updated_at=now,
    )
    created = repo.create_booking_request(db_path, booking)
    return {"booking": created.model_dump()}


@admin_router.put("/{request_id}/status")
def update_booking_status_endpoint(
    request_id: str,
    payload: BookingRequestStatusUpdate,
    request: Request,
    _=Depends(_admin),
):
    """Update booking request status."""
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    scoped = get_scoped_client_id(request)
    if scoped:
        br_client = repo.get_booking_request_client_id(db_path, request_id)
        if br_client and br_client != scoped:
            raise HTTPException(status_code=403, detail="forbidden: booking not in tenant scope")
    updated = repo.update_booking_status(
        db_path,
        request_id,
        payload.status,
        preferred_window=payload.preferred_window,
        location=payload.location,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="booking_request_not_found")
    return {"booking": updated.model_dump()}
