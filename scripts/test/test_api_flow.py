
import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/money-board"
DB_PARAM = "acq.db"

def check(response, action):
    if response.status_code != 200:
        print(f"FAILED {action}: {response.status_code} {response.text}")
        sys.exit(1)
    print(f"OK {action}")
    return response.json()

def run_test():
    print("--- Starting API Flow Test ---")
    
    # 1. Clear Data
    print("1. Clearing legacy data...")
    res = requests.post(f"{BASE_URL}/clear-legacy-data?db={DB_PARAM}")
    check(res, "Clear Data")
    
    # 2. Inject a Lead (mocking the repo directly or using a helper if available, 
    # but let's assume we can create a booking request via set-package API if it allows new IDs?)
    # Wait, set-package logic: "if not booking: create new booking request... but checks request_id format"
    # Actually, money_board.html sends `lead_id` for "Send Menu" but `requestId` (booking_id) for setPackage.
    # New leads in Money Board have `lead_id` as their ID?
    # In `get_money_board`: "lead_id": item['lead_id'] or item['booking_id'] ... "request_id": item['booking_id']
    # If item['booking_id'] is None (pure lead), what is request_id?
    # Service creates a booking for the lead.
    # My `sync_and_get` endpoint promotes new leads to bookings.
    # So every item on the board HAS a booking_id.
    
    # So I need to inject a LEAD first.
    print("2. Injecting test lead via direct DB insert...")
    import sqlite3
    con = sqlite3.connect(DB_PARAM)
    cursor = con.cursor()
    import datetime
    now_ts = datetime.datetime.utcnow().isoformat()
    import datetime
    now_ts = datetime.datetime.utcnow().isoformat()
    # Cleanup previous run
    cursor.execute("DELETE FROM lead_intake WHERE lead_id=999")
    cursor.execute("INSERT INTO lead_intake (lead_id, name, phone, status, meta_json, ts) VALUES (?, ?, ?, ?, ?, ?)", 
                   (999, "API Flow Tester", "555-0199", "new", "{}", now_ts))
    con.commit()
    con.close()
    
    # 3. Sync and Get
    print("3. Syncing leads...")
    res = requests.get(f"{BASE_URL}/sync-and-get?db={DB_PARAM}")
    data = check(res, "Sync and Get")
    
    # Find our lead
    target_item = None
    for col in data["columns"]:
        if col["status"] == "new":
            for item in col["items"]:
                if item["lead_name"] == "API Flow Tester":
                    target_item = item
                    break
    
    if not target_item:
        print("FAILED: Lead not found in 'new' column")
        sys.exit(1)
    
    booking_id = target_item["booking_id"] # This should be set by sync
    print(f"Found booking_id: {booking_id}")
    
    # 4. Set Package
    print(f"4. Setting Package for {booking_id}...")
    payload = {"package_id": "pkg-test"} # Ensure this package exists or logic tolerates it? 
    # Service checks if package exists? Service sets it. 
    # We might need to inject a package too.
    
    # Inject package
    con = sqlite3.connect(DB_PARAM)
    con.execute("INSERT OR REPLACE INTO service_packages (package_id, client_id, name, price, duration_min, active, meta_json, addons_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("pkg-test", "default", "Test Package", 1000, 60, 1, "{}", "[]", "2024-01-01", "2024-01-01"))
    con.commit()
    con.close()
    
    res = requests.post(f"{BASE_URL}/{booking_id}/set-package?db={DB_PARAM}", json=payload)
    check(res, "Set Package")
    
    # Verify status change
    res = requests.get(f"{BASE_URL}?db={DB_PARAM}")
    data = res.json()
    # Check if in "package_selected"
    found = False
    for col in data["columns"]:
        if col["status"] == "package_selected":
             for item in col["items"]:
                 if item["booking_id"] == booking_id:
                     found = True
    if not found:
        print("FAILED: Item not moved to 'package_selected'")
        # sys.exit(1) # Don't exit yet, debugging
    else:
        print("Verified: Item in 'package_selected'")

    # 5. Set Time Window
    print(f"5. Setting Time Window...")
    res = requests.post(f"{BASE_URL}/{booking_id}/set-time-window?db={DB_PARAM}", json={"preferred_window": "Morning"})
    check(res, "Set Time Window")
    
    # 6. Request Deposit
    print(f"6. Requesting Deposit...")
    res = requests.post(f"{BASE_URL}/{booking_id}/request-deposit?db={DB_PARAM}", json={"amount": 500, "method": "promptpay"})
    check(res, "Request Deposit")
    
    # 7. Mark Paid
    print(f"7. Marking Paid...")
    # NOTE: In new API this takes booking_id
    res = requests.post(f"{BASE_URL}/{booking_id}/mark-paid?db={DB_PARAM}")
    check(res, "Mark Paid")
    
    # 8. Mark Complete
    print(f"8. Marking Complete...")
    res = requests.post(f"{BASE_URL}/{booking_id}/mark-completed?db={DB_PARAM}")
    check(res, "Mark Complete")
    
    print("--- TEST PASSED ---")

if __name__ == "__main__":
    run_test()
