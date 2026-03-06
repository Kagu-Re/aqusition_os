"""Clear stale booking sessions from chat conversations.

This script removes pending_package_id and booking_state from conversation meta_json
to allow users to start fresh booking sessions during development.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

# Add src to path (run from project root)
_root = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, os.path.join(_root, "src"))

from ae.db import connect, init_db

def clear_stale_conversations(db_path: str, channel_id: Optional[str] = None, dry_run: bool = False):
    """Clear stale booking state from conversations.
    
    Args:
        db_path: Path to database
        channel_id: Optional channel_id to filter (e.g., 'ch_customer_telegram')
        dry_run: If True, only show what would be cleared without making changes
    """
    init_db(db_path)
    con = connect(db_path)
    
    try:
        cur = con.cursor()
        
        # Find conversations with booking state
        query = """SELECT conversation_id, channel_id, external_thread_id, meta_json, updated_at
                   FROM chat_conversations WHERE 1=1"""
        params = []
        
        if channel_id:
            query += " AND channel_id=?"
            params.append(channel_id)
        
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        
        cleared_count = 0
        total_count = len(rows)
        
        print(f"Found {total_count} conversation(s)")
        print("=" * 60)
        
        for row in rows:
            conv_id, ch_id, external_thread_id, meta_json_str, updated_at = row
            meta_json = json.loads(meta_json_str or "{}")
            
            has_pending = "pending_package_id" in meta_json
            has_state = "booking_state" in meta_json
            has_timeslot = "timeslot_list" in meta_json
            
            if has_pending or has_state or has_timeslot:
                print(f"\nConversation: {conv_id}")
                print(f"  Channel: {ch_id}")
                print(f"  Thread ID: {external_thread_id}")
                print(f"  Updated: {updated_at}")
                print(f"  Has pending_package_id: {has_pending} ({meta_json.get('pending_package_id', 'N/A')})")
                print(f"  Has booking_state: {has_state} ({meta_json.get('booking_state', 'N/A')})")
                print(f"  Has timeslot_list: {has_timeslot}")
                
                if not dry_run:
                    # Remove booking-related fields
                    new_meta = meta_json.copy()
                    new_meta.pop("pending_package_id", None)
                    new_meta.pop("booking_state", None)
                    new_meta.pop("timeslot_list", None)
                    
                    cur.execute(
                        """UPDATE chat_conversations 
                           SET meta_json=?, updated_at=datetime('now')
                           WHERE conversation_id=?""",
                        (json.dumps(new_meta), conv_id)
                    )
                    print(f"  [OK] Cleared booking state")
                    cleared_count += 1
                else:
                    print(f"  [DRY RUN] Would clear booking state")
                    cleared_count += 1
        
        if not dry_run:
            con.commit()
            print(f"\n[OK] Cleared {cleared_count} stale conversation(s)")
        else:
            print(f"\n[DRY RUN] Would clear {cleared_count} stale conversation(s)")
        
        if cleared_count == 0:
            print("\n[OK] No stale conversations found")
            
    finally:
        con.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clear stale booking sessions from chat conversations")
    parser.add_argument("--db", default="acq.db", help="Database path (default: acq.db)")
    parser.add_argument("--channel", help="Filter by channel_id (e.g., 'ch_customer_telegram')")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be cleared without making changes")
    
    args = parser.parse_args()
    
    db_path = args.db
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found: {db_path}")
        sys.exit(1)
    
    clear_stale_conversations(db_path, channel_id=args.channel, dry_run=args.dry_run)
