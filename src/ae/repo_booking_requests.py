from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import db
from .models import BookingRequest
from .event_bus import EventBus


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_datetime(dt_str: str) -> datetime:
    """Parse datetime string, handling malformed formats like '2026-02-07T11:58:55+00:00Z'."""
    if not dt_str:
        raise ValueError("Empty datetime string")
    
    # Remove trailing 'Z' if timezone offset is present (e.g., '+00:00Z' -> '+00:00')
    dt_str = re.sub(r'([+-]\d{2}:\d{2})Z$', r'\1', dt_str)
    
    # If ends with 'Z' and no timezone offset, replace with '+00:00'
    if dt_str.endswith('Z') and '+' not in dt_str and dt_str.count('-') <= 2:
        dt_str = dt_str[:-1] + '+00:00'
    
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        # Fallback: try parsing without timezone and assume UTC
        try:
            dt_str_clean = dt_str.replace('Z', '').rstrip('+-0123456789:')
            return datetime.fromisoformat(dt_str_clean).replace(tzinfo=timezone.utc)
        except ValueError:
            raise ValueError(f"Invalid datetime format: {dt_str}")


def create_booking_request(db_path: str, booking: BookingRequest) -> BookingRequest:
    """Create a new booking request and emit event."""
    # #region agent log
    import json as _json
    import time as _time
    try:
        with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
            _f.write(_json.dumps({"runId":"run1","hypothesisId":"B","location":"repo_booking_requests.py:40","message":"create_booking_request entry","data":{"request_id":booking.request_id,"lead_id":booking.lead_id,"package_id":booking.package_id,"preferred_window":booking.preferred_window},"timestamp":int(_time.time()*1000)})+"\n")
    except: pass
    # #endregion
    db.init_db(db_path)
    if isinstance(booking.created_at, datetime):
        # Ensure timezone-aware datetime
        if booking.created_at.tzinfo is None:
            booking.created_at = booking.created_at.replace(tzinfo=timezone.utc)
        created_at = booking.created_at.replace(microsecond=0).isoformat()
    else:
        created_at = booking.created_at or _now()
    updated_at = _now()
    meta_json = json.dumps(booking.meta_json or {}, ensure_ascii=False, separators=(",", ":"))
    
    con = db.connect(db_path)
    try:
        # #region agent log
        try:
            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"runId":"run1","hypothesisId":"B","location":"repo_booking_requests.py:55","message":"about to insert booking into database","data":{"request_id":booking.request_id,"lead_id":booking.lead_id,"package_id":booking.package_id},"timestamp":int(_time.time()*1000)})+"\n")
        except: pass
        # #endregion
        con.execute(
            """INSERT INTO booking_requests(
                request_id, lead_id, package_id, preferred_window, location, status, meta_json, created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                booking.request_id,
                booking.lead_id,
                booking.package_id,
                booking.preferred_window,
                booking.location,
                booking.status,
                meta_json,
                created_at,
                updated_at,
            ),
        )
        con.commit()
        # #region agent log
        try:
            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"runId":"run1","hypothesisId":"B","location":"repo_booking_requests.py:71","message":"booking inserted successfully","data":{"request_id":booking.request_id},"timestamp":int(_time.time()*1000)})+"\n")
        except: pass
        # #endregion
    except Exception as db_error:
        # #region agent log
        try:
            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"runId":"run1","hypothesisId":"B","location":"repo_booking_requests.py:73","message":"database insert failed","data":{"request_id":booking.request_id,"error":str(db_error)},"timestamp":int(_time.time()*1000)})+"\n")
        except: pass
        # #endregion
        raise
    finally:
        con.close()
    
    # Emit event for state machine
    if booking.status == "requested":
        try:
            EventBus.emit_topic(
                db_path,
                topic="op.booking.requested",
                aggregate_type="booking_request",
                aggregate_id=booking.request_id,
                payload={
                    "request_id": booking.request_id,
                    "lead_id": booking.lead_id,
                    "package_id": booking.package_id,
                    "status": booking.status,
                },
                actor="operator",
                correlation_id=f"lead:{booking.lead_id}",
                causation_id=None,
            )
        except Exception:
            # Best-effort: don't fail if event emission fails
            pass
    
    # Update LeadIntake booking_status
    try:
        from . import repo
        repo.update_lead_outcome(
            db_path,
            booking.lead_id,
            booking_status="booked",
        )
    except Exception:
        # Best-effort: don't fail if lead update fails
        pass
    
    return BookingRequest(
        request_id=booking.request_id,
        lead_id=booking.lead_id,
        package_id=booking.package_id,
        preferred_window=booking.preferred_window,
        location=booking.location,
        status=booking.status,
        meta_json=booking.meta_json or {},
        created_at=_parse_datetime(created_at),
        updated_at=_parse_datetime(updated_at),
    )


def get_booking_request_client_id(db_path: str, request_id: str) -> Optional[str]:
    """Return client_id for a booking request (via package)."""
    db.init_db(db_path)
    con = db.connect(db_path)
    try:
        row = db.fetchone(
            con,
            """SELECT sp.client_id FROM booking_requests br
               JOIN service_packages sp ON br.package_id = sp.package_id
               WHERE br.request_id = ?""",
            (request_id,),
        )
        return row["client_id"] if row and row.get("client_id") else None
    finally:
        con.close()


def get_booking_request(db_path: str, request_id: str) -> Optional[BookingRequest]:
    """Get a booking request by ID."""
    db.init_db(db_path)
    con = db.connect(db_path)
    try:
        row = db.fetchone(con, "SELECT * FROM booking_requests WHERE request_id=?", (request_id,))
        if not row:
            return None
        return BookingRequest(
            request_id=row["request_id"],
            lead_id=row["lead_id"],
            package_id=row["package_id"],
            preferred_window=row["preferred_window"],
            location=row["location"],
            status=row["status"],
            meta_json=json.loads(row["meta_json"] or "{}"),
            created_at=_parse_datetime(row["created_at"]),
            updated_at=_parse_datetime(row["updated_at"]),
        )
    finally:
        con.close()


def get_recent_booking_request(
    db_path: str,
    *,
    lead_id: int,
    package_id: str,
    preferred_window: str,
    within_seconds: int = 30,
) -> Optional[BookingRequest]:
    """Check for a recent duplicate booking request.
    
    Returns a booking request if one exists with the same lead_id, package_id, and preferred_window
    created within the specified time window.
    """
    db.init_db(db_path)
    from datetime import timedelta
    
    # Calculate cutoff time
    cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=within_seconds)
    cutoff_str = cutoff_time.replace(microsecond=0).isoformat()
    
    con = db.connect(db_path)
    try:
        row = db.fetchone(
            con,
            """SELECT * FROM booking_requests 
               WHERE lead_id=? AND package_id=? AND preferred_window=? 
               AND created_at >= ? AND status='requested'
               ORDER BY created_at DESC LIMIT 1""",
            (lead_id, package_id, preferred_window, cutoff_str)
        )
        if not row:
            return None
        return BookingRequest(
            request_id=row["request_id"],
            lead_id=row["lead_id"],
            package_id=row["package_id"],
            preferred_window=row["preferred_window"],
            location=row["location"],
            status=row["status"],
            meta_json=json.loads(row["meta_json"] or "{}"),
            created_at=_parse_datetime(row["created_at"]),
            updated_at=_parse_datetime(row["updated_at"]),
        )
    finally:
        con.close()


def list_booking_requests(
    db_path: str,
    *,
    lead_id: Optional[int] = None,
    status: Optional[str] = None,
    client_id: Optional[str] = None,
    limit: int = 50,
) -> List[BookingRequest]:
    """List booking requests with optional filters.
    When client_id is set, filters via package→client linkage."""
    db.init_db(db_path)
    sql = "SELECT br.* FROM booking_requests br"
    params: List[Any] = []
    where: List[str] = []
    if client_id:
        sql += " JOIN service_packages sp ON br.package_id = sp.package_id"
        where.append("sp.client_id=?")
        params.append(client_id)
    if lead_id:
        where.append("br.lead_id=?")
        params.append(lead_id)
    if status:
        where.append("br.status=?")
        params.append(status)
    if where:
        sql += " WHERE " + " AND ".join(where)
    
    sql += " ORDER BY br.updated_at DESC LIMIT ?"
    params.append(limit)
    
    con = db.connect(db_path)
    try:
        rows = db.fetchall(con, sql, tuple(params))
        out: List[BookingRequest] = []
        for r in rows:
            out.append(BookingRequest(
                request_id=r["request_id"],
                lead_id=r["lead_id"],
                package_id=r["package_id"],
                preferred_window=r["preferred_window"],
                location=r["location"],
                status=r["status"],
                meta_json=json.loads(r["meta_json"] or "{}"),
                created_at=_parse_datetime(r["created_at"]),
                updated_at=_parse_datetime(r["updated_at"]),
            ))
        return out
    finally:
        con.close()


def get_active_bookings_for_lead(
    db_path: str,
    lead_id: int,
    *,
    exclude_statuses: Optional[List[str]] = None,
) -> List[BookingRequest]:
    """Get active booking requests for a lead.
    
    Args:
        db_path: Database path
        lead_id: Lead ID to search for
        exclude_statuses: List of statuses to exclude (default: ['completed', 'closed', 'cancelled'])
    
    Returns:
        List of active booking requests
    """
    db.init_db(db_path)
    if exclude_statuses is None:
        exclude_statuses = ['completed', 'closed', 'cancelled', 'canceled']
    
    con = db.connect(db_path)
    try:
        placeholders = ','.join(['?'] * len(exclude_statuses))
        sql = f"""SELECT * FROM booking_requests 
                  WHERE lead_id=? AND status NOT IN ({placeholders})
                  ORDER BY created_at DESC"""
        params = [lead_id] + exclude_statuses
        
        rows = db.fetchall(con, sql, tuple(params))
        out: List[BookingRequest] = []
        for r in rows:
            out.append(BookingRequest(
                request_id=r["request_id"],
                lead_id=r["lead_id"],
                package_id=r["package_id"],
                preferred_window=r["preferred_window"],
                location=r["location"],
                status=r["status"],
                meta_json=json.loads(r["meta_json"] or "{}"),
                created_at=_parse_datetime(r["created_at"]),
                updated_at=_parse_datetime(r["updated_at"]),
            ))
        return out
    finally:
        con.close()


def cancel_booking_request(
    db_path: str,
    request_id: str,
    actor: str = "user",
) -> Optional[BookingRequest]:
    """Cancel a booking request by setting status to 'cancelled'."""
    return update_booking_status(db_path, request_id, "cancelled", actor=actor)


def update_booking_status(
    db_path: str,
    request_id: str,
    status: str,
    preferred_window: Optional[str] = None,
    location: Optional[str] = None,
    actor: str = "operator",
) -> Optional[BookingRequest]:
    """Update booking request status and emit appropriate event."""
    db.init_db(db_path)
    updated_at = _now()
    
    con = db.connect(db_path)
    try:
        # Get existing record
        existing = db.fetchone(con, "SELECT * FROM booking_requests WHERE request_id=?", (request_id,))
        if not existing:
            return None
        
        # Determine event topic based on status transition
        old_status = existing["status"]
        event_topic = None
        
        if status == "deposit_requested" and old_status == "requested":
            event_topic = "op.booking.deposit_requested"
        elif status == "confirmed" and old_status == "deposit_requested":
            event_topic = "op.booking.confirmed"
        elif status == "completed" and old_status == "confirmed":
            event_topic = "op.booking.completed"
        elif status == "closed" and old_status == "completed":
            event_topic = "op.booking.closed"
        elif status in ("cancelled", "canceled") and old_status not in ("cancelled", "canceled", "closed", "completed"):
            event_topic = "op.booking.cancelled"
        
        # Update database
        update_fields = ["status=?", "updated_at=?"]
        update_values = [status, updated_at]
        
        if preferred_window is not None:
            update_fields.append("preferred_window=?")
            update_values.append(preferred_window)
        
        if location is not None:
            update_fields.append("location=?")
            update_values.append(location)
        
        update_values.append(request_id)
        
        con.execute(
            f"UPDATE booking_requests SET {', '.join(update_fields)} WHERE request_id=?",
            tuple(update_values),
        )
        con.commit()
        
        # Emit event if status changed
        if event_topic:
            try:
                EventBus.emit_topic(
                    db_path,
                    topic=event_topic,
                    aggregate_type="booking_request",
                    aggregate_id=request_id,
                    payload={
                        "request_id": request_id,
                        "lead_id": existing["lead_id"],
                        "old_status": old_status,
                        "new_status": status,
                    },
                    actor=actor,
                    correlation_id=f"lead:{existing['lead_id']}",
                    causation_id=None,
                )
            except Exception:
                # Best-effort: don't fail if event emission fails
                pass
        
        # Update LeadIntake if status is confirmed
        if status == "confirmed":
            try:
                from . import repo
                repo.update_lead_outcome(
                    db_path,
                    existing["lead_id"],
                    booking_status="confirmed",
                )
            except Exception:
                # Best-effort: don't fail if lead update fails
                pass
        
    finally:
        con.close()
    
    # Return updated record
    return get_booking_request(db_path, request_id)
