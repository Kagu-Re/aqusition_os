"""Clear booking requests with status 'requested' for development.

This script deletes all booking requests with status 'requested' to allow
clean testing during development. Use with caution - this permanently
deletes booking data.
"""

import os
import sys
from pathlib import Path

# Add src to path (run from project root)
_root = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, os.path.join(_root, "src"))

from ae.db import connect, init_db

def clear_dev_booking_requests(db_path: str, dry_run: bool = False):
    """Clear all booking requests with status 'requested'.
    
    Args:
        db_path: Path to database
        dry_run: If True, only show what would be deleted without making changes
    """
    init_db(db_path)
    con = connect(db_path)
    
    try:
        cur = con.cursor()
        
        # Count bookings to be deleted
        cur.execute("SELECT COUNT(*) FROM booking_requests WHERE status='requested'")
        count = cur.fetchone()[0]
        
        if count == 0:
            print("[OK] No booking requests with status 'requested' found")
            return
        
        print(f"Found {count} booking request(s) with status 'requested'")
        
        if dry_run:
            # Show what would be deleted
            cur.execute("SELECT request_id, lead_id, package_id, preferred_window, created_at FROM booking_requests WHERE status='requested' ORDER BY created_at DESC LIMIT 10")
            rows = cur.fetchall()
            print("\nSample bookings that would be deleted:")
            for row in rows:
                print(f"  - {row[0]}: lead={row[1]}, package={row[2]}, timeslot={row[3]}, created={row[4]}")
            if count > 10:
                print(f"  ... and {count - 10} more")
            print(f"\n[DRY RUN] Would delete {count} booking request(s)")
        else:
            # Delete bookings
            cur.execute("DELETE FROM booking_requests WHERE status='requested'")
            con.commit()
            print(f"[OK] Deleted {count} booking request(s)")
            
    finally:
        con.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clear booking requests with status 'requested' for development")
    parser.add_argument("--db", default="acq.db", help="Database path (default: acq.db)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without making changes")
    
    args = parser.parse_args()
    
    db_path = args.db
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found: {db_path}")
        sys.exit(1)
    
    clear_dev_booking_requests(db_path, dry_run=args.dry_run)
