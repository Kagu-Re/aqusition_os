#!/usr/bin/env python3
"""Check bot state - active bookings, conversations, and cached data."""

import sys
from src.ae.repo_booking_requests import list_booking_requests, get_active_bookings_for_lead
from src.ae.repo_chat_conversations import list_conversations
from src.ae.repo_leads import list_leads

def check_bot_state(db_path: str = "acq.db"):
    """Check bot state for issues."""
    print(f"[CheckBotState] Checking bot state (db: {db_path})\n")
    
    # 1. Check active bookings
    print("=" * 60)
    print("ACTIVE BOOKINGS")
    print("=" * 60)
    all_bookings = list_booking_requests(db_path, limit=100)
    active_bookings = [b for b in all_bookings if b.status not in ['completed', 'closed', 'cancelled']]
    
    if active_bookings:
        print(f"Found {len(active_bookings)} active booking(s):\n")
        for booking in active_bookings:
            print(f"  Booking ID: {booking.request_id}")
            print(f"  Lead ID: {booking.lead_id}")
            print(f"  Package ID: {booking.package_id}")
            print(f"  Status: {booking.status}")
            print(f"  Created: {booking.created_at}")
            print(f"  Preferred Window: {booking.preferred_window}")
            print()
    else:
        print("No active bookings found.\n")
    
    # 2. Check all bookings (including completed/cancelled)
    print("=" * 60)
    print("ALL BOOKINGS (last 20)")
    print("=" * 60)
    recent_bookings = all_bookings[:20]
    if recent_bookings:
        for booking in recent_bookings:
            print(f"  [{booking.status}] ID: {booking.request_id}, Lead: {booking.lead_id}, Package: {booking.package_id}, Created: {booking.created_at}")
    else:
        print("No bookings found.\n")
    
    # 3. Check conversations with pending state
    print("=" * 60)
    print("CONVERSATIONS WITH BOOKING STATE")
    print("=" * 60)
    all_conversations = list_conversations(db_path, limit=100)
    conversations_with_state = [
        c for c in all_conversations 
        if c.meta_json.get("booking_state") or c.meta_json.get("pending_package_id")
    ]
    
    if conversations_with_state:
        print(f"Found {len(conversations_with_state)} conversation(s) with booking state:\n")
        for conv in conversations_with_state:
            print(f"  Conversation ID: {conv.conversation_id}")
            print(f"  Channel ID: {conv.channel_id}")
            print(f"  External Thread ID: {conv.external_thread_id}")
            print(f"  Booking State: {conv.meta_json.get('booking_state')}")
            print(f"  Pending Package ID: {conv.meta_json.get('pending_package_id')}")
            print(f"  Timeslot List: {conv.meta_json.get('timeslot_list')}")
            print()
    else:
        print("No conversations with booking state found.\n")
    
    # 4. Check leads
    print("=" * 60)
    print("LEADS (last 10)")
    print("=" * 60)
    leads = list_leads(db_path, limit=10)
    if leads:
        for lead in leads:
            active_lead_bookings = get_active_bookings_for_lead(db_path, lead.lead_id)
            print(f"  Lead ID: {lead.lead_id}, Name: {lead.name}, Phone: {lead.phone}, Active Bookings: {len(active_lead_bookings)}")
    else:
        print("No leads found.\n")
    
    # 5. Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total active bookings: {len(active_bookings)}")
    print(f"Total conversations with state: {len(conversations_with_state)}")
    print(f"\nIf you see multiple active bookings for the same lead, that could cause")
    print(f"multiple /start commands to fire. Use reset_telegram_bot.py to clear state.")

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "acq.db"
    check_bot_state(db_path)
