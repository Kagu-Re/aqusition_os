#!/usr/bin/env python3
"""Test the full service package selection flow and verify DOD criteria."""

import sys
import os
# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo
from datetime import datetime, timedelta
import json

db_path = 'acq.db'
page_id = 'demo-service-page'
client_id = 'test-massage-spa'

print("=" * 60)
print("Service Package Flow - Definition of Done (DOD) Verification")
print("=" * 60)
print()

# Get recent events (last 5 minutes)
cutoff_time = datetime.now() - timedelta(minutes=5)
all_events = repo.list_events(db_path)
recent_events = [e for e in all_events if e.timestamp >= cutoff_time]

print(f"[1] Event Tracking Check")
print(f"    Total events in DB: {len(all_events)}")
print(f"    Recent events (last 5 min): {len(recent_events)}")

package_events = [e for e in recent_events if e.event_name.value == 'package_selected']
if package_events:
    print(f"    ✅ Found {len(package_events)} package_selected events")
    for i, e in enumerate(package_events, 1):
        print(f"       [{i}] Page: {e.page_id}, Time: {e.timestamp}")
        params = e.params_json
        if 'package_id' in params:
            print(f"           Package ID: {params.get('package_id')}")
            print(f"           Package Name: {params.get('package_name')}")
            print(f"           Package Price: ${params.get('package_price', 0):.2f}")
else:
    print(f"    ❌ No package_selected events found")
    print(f"       Recent event types: {set(e.event_name.value for e in recent_events)}")

print()

# Get recent leads (last 5 minutes)
print(f"[2] Lead Creation Check")
all_leads = repo.list_leads(db_path, limit=100)
recent_leads = [l for l in all_leads if l.client_id == client_id]

package_leads = []
for lead in recent_leads:
    if lead.meta_json and ('package_id' in lead.meta_json or 'package_name' in lead.meta_json):
        package_leads.append(lead)

if package_leads:
    print(f"    ✅ Found {len(package_leads)} leads with package metadata")
    for i, lead in enumerate(package_leads[:3], 1):
        print(f"       [{i}] Lead ID: {lead.lead_id}")
        print(f"           Message: {lead.message}")
        print(f"           Meta: {json.dumps(lead.meta_json, indent=12)}")
else:
    print(f"    ❌ No leads with package metadata found")
    if recent_leads:
        print(f"       Recent leads for client: {len(recent_leads)}")
        print(f"       Latest lead message: {recent_leads[0].message if recent_leads else 'N/A'}")

print()

# Check chat channel
print(f"[3] Chat Channel Check")
channels = repo.list_chat_channels(db_path)
client_channels = [ch for ch in channels if ch.meta_json.get('client_id') == client_id]

if client_channels:
    ch = client_channels[0]
    print(f"    ✅ Chat channel configured")
    print(f"       Provider: {ch.provider.value}")
    print(f"       Handle: {ch.handle}")
    print(f"       Display Name: {ch.display_name}")
    
    # Generate expected URL
    if ch.provider.value == 'telegram':
        handle_clean = ch.handle.replace('@', '')
        expected_url = f"https://t.me/{handle_clean}?package={{package_id}}"
    else:
        expected_url = f"Chat URL with package parameter"
    print(f"       Expected redirect format: {expected_url}")
else:
    print(f"    ❌ No chat channel found for client: {client_id}")

print()

# Check service packages
print(f"[4] Service Packages Check")
packages = repo.list_packages(db_path, client_id=client_id, active=True)
if packages:
    print(f"    ✅ Found {len(packages)} active service packages")
    for i, pkg in enumerate(packages[:3], 1):
        print(f"       [{i}] {pkg.name} - ${pkg.price:.2f} ({pkg.duration_min} min)")
else:
    print(f"    ❌ No service packages found for client: {client_id}")

print()

# Summary
print("=" * 60)
print("Summary")
print("=" * 60)

checks_passed = 0
checks_total = 4

if package_events:
    checks_passed += 1
    print("✅ Event tracking: PASSED")
else:
    print("❌ Event tracking: FAILED - No package_selected events found")

if package_leads:
    checks_passed += 1
    print("✅ Lead creation: PASSED")
else:
    print("❌ Lead creation: FAILED - No leads with package metadata")

if client_channels:
    checks_passed += 1
    print("✅ Chat channel: PASSED")
else:
    print("❌ Chat channel: FAILED - No channel configured")

if packages:
    checks_passed += 1
    print("✅ Service packages: PASSED")
else:
    print("❌ Service packages: FAILED - No packages found")

print()
print(f"Result: {checks_passed}/{checks_total} checks passed")

if checks_passed == checks_total:
    print("🎉 All DOD criteria met! Flow is working correctly.")
else:
    print("⚠️  Some checks failed. Review the output above and fix issues.")

print()
