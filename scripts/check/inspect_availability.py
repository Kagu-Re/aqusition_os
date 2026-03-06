#!/usr/bin/env python3
"""Inspect availability calculation and display."""

import sys
import os
# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

import requests
import json
from ae import repo
from ae.repo_booking_requests import list_booking_requests

db_path = 'acq.db'
client_id = 'test-massage-spa'

print("=" * 80)
print("AVAILABILITY INSPECTION")
print("=" * 80)
print()

# 1. Check packages and their meta_json
print("1. PACKAGE METADATA:")
print("-" * 80)
packages = repo.list_packages(db_path, client_id=client_id, active=True)
for pkg in packages:
    print(f"  {pkg.package_id}:")
    print(f"    Name: {pkg.name}")
    print(f"    meta_json: {pkg.meta_json}")
    max_cap = pkg.meta_json.get('max_capacity')
    explicit_slots = pkg.meta_json.get('available_slots')
    print(f"    max_capacity: {max_cap}")
    print(f"    available_slots (explicit): {explicit_slots}")
    print()

# 2. Check BookingRequest records
print("2. BOOKING REQUESTS:")
print("-" * 80)
bookings = list_booking_requests(db_path, limit=100)
print(f"  Total bookings: {len(bookings)}")
if bookings:
    for br in bookings:
        print(f"  - {br.request_id}: package_id={br.package_id}, status={br.status}")
else:
    print("  (no bookings found)")
print()

# 3. Check client default_available_slots
print("3. CLIENT DEFAULT AVAILABILITY:")
print("-" * 80)
client = repo.get_client(db_path, client_id)
client_config = client.service_config_json or {}
default_slots = client_config.get('default_available_slots')
print(f"  default_available_slots: {default_slots}")
print()

# 4. Test API response
print("4. API RESPONSE:")
print("-" * 80)
try:
    url = "http://localhost:8001/v1/service-packages"
    params = {
        "client_id": client_id,
        "page_id": "test-massage-spa-premium",
        "active": "true",
        "db": db_path
    }
    r = requests.get(url, params=params)
    data = r.json()
    
    print(f"  API returned {data['count']} packages:")
    for pkg in data['items']:
        avail = pkg.get('available_slots')
        print(f"  - {pkg['package_id']}: available_slots={avail}")
        if avail is None:
            print(f"    ⚠️  No availability data!")
        elif avail == 0:
            print(f"    🔴 Fully booked")
        elif avail == 1:
            print(f"    🟠 Only 1 slot left!")
        elif avail <= 3:
            print(f"    🟡 Only {avail} slots left")
        else:
            print(f"    🟢 {avail} slots available")
except Exception as e:
    print(f"  ❌ Error calling API: {e}")
print()

# 5. Check what should be displayed
print("5. EXPECTED DISPLAY:")
print("-" * 80)
print("  Based on availability values:")
print("  - 0 slots: Red badge 'Fully booked', disabled button")
print("  - 1 slot: Red badge 'Only 1 slot left!', urgent CTA")
print("  - 2-3 slots: Orange badge 'Only X slots left', urgent CTA")
print("  - 4+ slots: Green badge 'Available' or no badge")
print()
