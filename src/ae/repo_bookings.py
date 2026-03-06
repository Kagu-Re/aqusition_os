from datetime import datetime, timezone
import json
from typing import Optional, List, Dict, Any
import sqlite3
from .models import Booking, Customer, BookingEvent
from .db import connect, Transaction

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

# --- Customer Repo ---

def create_customer(db_path: str, customer: Customer) -> str:
    with Transaction(db_path) as con:
        con.execute("""
            INSERT INTO customers (
                customer_id, client_id, display_name, phone, email, 
                telegram_id, telegram_username, line_id, whatsapp_id, 
                language_pref, notes, tags_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer.customer_id, customer.client_id, customer.display_name,
            customer.phone, customer.email, customer.telegram_id,
            customer.telegram_username, customer.line_id, customer.whatsapp_id,
            customer.language_pref, customer.notes, json.dumps(customer.tags),
            customer.created_at.isoformat(), customer.updated_at.isoformat()
        ))
        return customer.customer_id

def get_customer(db_path: str, customer_id: str) -> Optional[Customer]:
    con = connect(db_path)
    row = con.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,)).fetchone()
    con.close()
    if not row:
        return None
    
    d = dict(row)
    d['tags'] = json.loads(d['tags_json'])
    return Customer(**d)

def get_customer_by_telegram_id(db_path: str, telegram_id: str) -> Optional[Customer]:
    con = connect(db_path)
    row = con.execute("SELECT * FROM customers WHERE telegram_id = ?", (telegram_id,)).fetchone()
    con.close()
    if not row:
        return None
    
    d = dict(row)
    d['tags'] = json.loads(d['tags_json'])
    return Customer(**d)

def create_customer_from_lead(
    db_path: str,
    lead_id: int,
    telegram_id: str = None,
    telegram_username: str = None
) -> Customer:
    """Create a customer from a lead."""
    from .repo_leads import get_lead
    from uuid import uuid4
    
    lead = get_lead(db_path, lead_id)
    if not lead:
        raise ValueError(f"Lead {lead_id} not found")
    
    # Generate customer ID
    customer_id = f"cust_{uuid4().hex[:12]}"
    
    # Create customer from lead data
    customer = Customer(
        customer_id=customer_id,
        client_id=lead.client_id,
        display_name=lead.name or "Customer",
        phone=lead.phone,
        email=lead.email,
        telegram_id=str(telegram_id) if telegram_id else None,
        telegram_username=telegram_username,
        language_pref="en",
        tags=[],
        created_at=_now(),
        updated_at=_now()
    )
    
    create_customer(db_path, customer)
    return customer

def create_booking(db_path: str, booking: Booking) -> str:
    # Ensure addons is list
    addons_json = json.dumps(booking.addons)
    tags_json = json.dumps(booking.tags)
    
    with Transaction(db_path) as con:
        con.execute("""
            INSERT INTO bookings (
                booking_id, client_id, customer_id, lead_id,
                channel, status, status_reason,
                package_id, package_name_snapshot, price_amount, currency, duration_minutes,
                addons_json, quantity,
                preferred_time_window, preferred_date, final_slot_start, final_slot_end,
                deposit_required, deposit_amount, deposit_status, payment_link, payment_ref,
                tags_json, notes_internal, created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?
            )
        """, (
            booking.booking_id, booking.client_id, booking.customer_id, booking.lead_id,
            booking.channel, booking.status, booking.status_reason,
            booking.package_id, booking.package_name_snapshot, booking.price_amount, booking.currency, booking.duration_minutes,
            addons_json, booking.quantity,
            booking.preferred_time_window, booking.preferred_date, 
            booking.final_slot_start.isoformat() if booking.final_slot_start else None,
            booking.final_slot_end.isoformat() if booking.final_slot_end else None,
            1 if booking.deposit_required else 0, booking.deposit_amount, booking.deposit_status, booking.payment_link, booking.payment_ref,
            tags_json, booking.notes_internal,
            booking.created_at.isoformat(), booking.updated_at.isoformat()
        ))
        return booking.booking_id

def get_booking(db_path: str, booking_id: str) -> Optional[Booking]:
    con = connect(db_path)
    row = con.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()
    con.close()
    if not row:
        return None
    
    d = dict(row)
    # Parse JSON fields
    d['addons'] = json.loads(d['addons_json'])
    d['tags'] = json.loads(d['tags_json'])
    d['created_at'] = datetime.fromisoformat(d['created_at'])
    d['updated_at'] = datetime.fromisoformat(d['updated_at'])
    if d['final_slot_start']:
        d['final_slot_start'] = datetime.fromisoformat(d['final_slot_start'])
    if d['final_slot_end']:
        d['final_slot_end'] = datetime.fromisoformat(d['final_slot_end'])
        
    return Booking(**d)

def update_booking_status(db_path: str, booking_id: str, new_status: str, actor_type: str, actor_id: str, reason: str = None) -> None:
    ts = _now()
    with Transaction(db_path) as con:
        # Get current status for diff
        cur = con.execute("SELECT status FROM bookings WHERE booking_id = ?", (booking_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Booking {booking_id} not found")
        old_status = row['status']
        
        # Update
        con.execute("""
            UPDATE bookings 
            SET status = ?, status_reason = ?, updated_at = ? 
            WHERE booking_id = ?
        """, (new_status, reason, ts, booking_id))
        
        # Log event
        event_id = f"evt_{int(datetime.now().timestamp()*1000)}"
        diff = {"before": {"status": old_status}, "after": {"status": new_status, "reason": reason}}
        con.execute("""
            INSERT INTO booking_events (
                event_id, booking_id, timestamp, event_type, 
                actor_type, actor_id, diff_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id, booking_id, ts, "STATE_CHANGED",
            actor_type, actor_id, json.dumps(diff)
        ))

def update_booking_fields(db_path: str, booking_id: str, updates: Dict[str, Any], actor_type: str, actor_id: str) -> None:
    """Generic update for non-status fields, logs event."""
    if not updates:
        return
        
    ts = _now()
    set_clauses = []
    params = []
    for k, v in updates.items():
        set_clauses.append(f"{k} = ?")
        # Handle JSON fields serialization
        if k in ['addons_json', 'tags_json'] and isinstance(v, list):
             params.append(json.dumps(v))
        elif k in ['created_at', 'updated_at', 'final_slot_start', 'final_slot_end'] and isinstance(v, datetime):
            params.append(v.isoformat())
        else:
            params.append(v)
            
    params.append(ts)
    params.append(booking_id)
    
    sql = f"UPDATE bookings SET {', '.join(set_clauses)}, updated_at = ? WHERE booking_id = ?"
    
    with Transaction(db_path) as con:
        # We could query old values for diff but for speed we might skip or do a lightweight check
        # For strict audit, let's query old.
        cur = con.execute(f"SELECT {', '.join(updates.keys())} FROM bookings WHERE booking_id = ?", (booking_id,))
        row = cur.fetchone()
        old_data = dict(row) if row else {}
        
        con.execute(sql, params)
        
        # Log event
        event_id = f"evt_{int(datetime.now().timestamp()*1000)}"
        diff = {"before": old_data, "after": updates}
        con.execute("""
            INSERT INTO booking_events (
                event_id, booking_id, timestamp, event_type, 
                actor_type, actor_id, diff_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id, booking_id, ts, "UPDATED",
            actor_type, actor_id, json.dumps(diff)
        ))

def get_money_board_bookings(db_path: str, client_id: str = None) -> List[Dict[str, Any]]:
    """Get bookings formatted for Money Board display."""
    sql = """
        SELECT b.*, c.display_name, c.phone, c.email 
        FROM bookings b
        JOIN customers c ON b.customer_id = c.customer_id
    """
    params = []
    if client_id:
        sql += " WHERE b.client_id = ?"
        params.append(client_id)
        
    sql += " ORDER BY b.updated_at DESC"
    
    con = connect(db_path)
    rows = con.execute(sql, params).fetchall()
    con.close()
    
    results = []
    for row in rows:
        d = dict(row)
        # Parse JSON fields
        d['addons'] = json.loads(d['addons_json'])
        d['tags'] = json.loads(d['tags_json'])
        results.append(d)
    return results

def get_active_bookings_for_customer(db_path: str, customer_id: str) -> List[Booking]:
    con = connect(db_path)
    sql = """
        SELECT * FROM bookings 
        WHERE customer_id = ? 
        AND status NOT IN ('CLOSED', 'CANCELLED', 'COMPLETE', 'EXPIRED')
    """
    rows = con.execute(sql, (customer_id,)).fetchall()
    con.close()
    
    results = []
    for row in rows:
        d = dict(row)
        d['addons'] = json.loads(d['addons_json'])
        d['tags'] = json.loads(d['tags_json'])
        d['created_at'] = datetime.fromisoformat(d['created_at'])
        d['updated_at'] = datetime.fromisoformat(d['updated_at'])
        if d['final_slot_start']:
            d['final_slot_start'] = datetime.fromisoformat(d['final_slot_start'])
        if d['final_slot_end']:
            d['final_slot_end'] = datetime.fromisoformat(d['final_slot_end'])
            
        results.append(Booking(**d))
    return results

def get_bookings_by_status(db_path: str, status: str, limit: int = 20) -> List[Booking]:
    con = connect(db_path)
    sql = """
        SELECT * FROM bookings 
        WHERE status = ? 
        ORDER BY updated_at DESC
        LIMIT ?
    """
    rows = con.execute(sql, (status, limit)).fetchall()
    con.close()
    
    results = []
    for row in rows:
        d = dict(row)
        d['addons'] = json.loads(d['addons_json'])
        d['tags'] = json.loads(d['tags_json'])
        d['created_at'] = datetime.fromisoformat(d['created_at'])
        d['updated_at'] = datetime.fromisoformat(d['updated_at'])
        if d['final_slot_start']:
            d['final_slot_start'] = datetime.fromisoformat(d['final_slot_start'])
        if d['final_slot_end']:
            d['final_slot_end'] = datetime.fromisoformat(d['final_slot_end'])
            
        results.append(Booking(**d))
    return results
