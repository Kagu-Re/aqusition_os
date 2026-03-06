import sys
import os

# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

try:
    print("Importing repo_bookings...")
    from ae import repo_bookings
    print("Success repo_bookings.")
    
    print("Importing service_booking...")
    from ae import service_booking
    print("Success service_booking.")

    print("Importing console_routes_money_board...")
    from ae import console_routes_money_board
    print("Success console_routes_money_board.")

except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
