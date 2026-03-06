#!/usr/bin/env python3
"""Test availability display logic."""

import requests
import json

url = "http://localhost:8001/v1/service-packages"
params = {
    "client_id": "test-massage-spa",
    "page_id": "test-massage-spa-premium",
    "active": "true",
    "db": "acq.db"
}

r = requests.get(url, params=params)
data = r.json()

print("AVAILABILITY DISPLAY TEST")
print("=" * 80)
print()

for pkg in data['items']:
    avail = pkg.get('available_slots')
    print(f"Package: {pkg['name']}")
    print(f"  available_slots: {avail}")
    
    if avail is None:
        print(f"  Display: No badge (availability not set)")
    elif avail == 0:
        print(f"  Display: 🔴 'Fully booked' (red badge, disabled button)")
    elif avail == 1:
        print(f"  Display: 🔴 'Only 1 slot left!' (red badge, urgent CTA)")
    elif avail <= 3:
        print(f"  Display: 🟠 'Only {avail} slots left' (orange badge, urgent CTA)")
    else:
        print(f"  Display: 🟢 'Available' (green badge) or no badge")
    print()
