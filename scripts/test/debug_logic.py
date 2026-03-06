import sys
import os
from typing import Dict, Any, List

# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))
from ae import repo

# Mock request and check logic
def test_logic():
    print("Testing get_money_board_bookings...")
    db_path = "d:/aqusition_os/acq.db"
    try:
        items = repo.get_money_board_bookings(db_path, None)
        print(f"Items: {len(items)}")
        for i in items:
            print(i)
    except Exception as e:
        print(f"Repo Error: {e}")
        import traceback
        traceback.print_exc()
        return

    print("Testing transformation logic...")
    columns: Dict[str, List[Dict[str, Any]]] = {status: [] for status in ["new", "confirmed"]} # Simplified
    
    try:
        for item in items:
            row = {
                "lead_id": item['lead_id'] or item['booking_id'],
                "booking_id": item['booking_id'],
                "lead_name": item['display_name'],
                "status": item['status'].lower()
            }
            print(f"Row: {row}")
    except Exception as e:
        print(f"Transform Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_logic()
