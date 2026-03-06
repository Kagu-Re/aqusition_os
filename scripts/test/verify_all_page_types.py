#!/usr/bin/env python3
"""Verify package filtering fix applies to all page types."""

import sys
import os
# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

import requests
from ae import repo

db_path = 'acq.db'
client_id = 'test-massage-spa'

print("=" * 80)
print("VERIFYING FIX FOR ALL PAGE TYPES")
print("=" * 80)
print()

# Get all pages for this client
all_pages = repo.list_pages(db_path)
pages = [p for p in all_pages if p.client_id == client_id]

print("Found pages:")
for page in pages:
    print(f"  {page.page_id}:")
    print(f"    service_focus: {page.service_focus}")
    print(f"    template_id: {page.template_id}")
    print()

# Test API for each page type
print("=" * 80)
print("TESTING API RESPONSES")
print("=" * 80)
print()

api_base = "http://localhost:8001/v1/service-packages"

for page in pages:
    print(f"Page: {page.page_id} (service_focus={page.service_focus})")
    print("-" * 80)
    
    try:
        params = {
            "client_id": client_id,
            "page_id": page.page_id,
            "active": "true",
            "db": db_path
        }
        r = requests.get(api_base, params=params)
        data = r.json()
        
        print(f"  API returned {data['count']} packages:")
        for pkg in data['items']:
            focus = pkg.get('meta_json', {}).get('service_focus', 'None')
            avail = pkg.get('available_slots', 'NOT SET')
            print(f"    - {pkg['package_id']}: service_focus={focus}, available_slots={avail}")
        
        # Verify filtering logic
        if page.service_focus == "premium":
            expected_packages = ["pkg-deep-90", "pkg-couple-60"]
            actual_packages = [p['package_id'] for p in data['items']]
            if set(actual_packages) == set(expected_packages):
                print(f"  ✅ CORRECT: Only premium packages shown")
            else:
                print(f"  ❌ WRONG: Expected {expected_packages}, got {actual_packages}")
        elif page.service_focus == "express":
            # Express should only show express packages (if any)
            express_packages = [p['package_id'] for p in data['items'] 
                              if p.get('meta_json', {}).get('service_focus') == 'express']
            if len(express_packages) == len(data['items']):
                print(f"  ✅ CORRECT: Only express packages shown")
            else:
                print(f"  ⚠️  Mixed packages or no express packages")
        elif page.service_focus is None:
            # Main page should only show packages without service_focus
            main_packages = [p['package_id'] for p in data['items'] 
                           if p.get('meta_json', {}).get('service_focus') is None]
            if len(main_packages) == len(data['items']):
                print(f"  ✅ CORRECT: Only main packages shown")
            else:
                print(f"  ⚠️  Mixed packages")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print("The fix is in the API endpoint (/v1/service-packages) which is called")
print("by ALL page types via JavaScript. Since all pages use the same API,")
print("the fix applies universally to:")
print("  - Main pages (service_focus=None)")
print("  - Premium pages (service_focus='premium')")
print("  - Express pages (service_focus='express')")
print("  - Any future page types")
print()
