#!/usr/bin/env python3
"""Check if package_selected events were tracked."""

import sys
import os
# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo
import json

db_path = 'acq.db'

# Get all recent events
all_events = repo.list_events(db_path)
print(f'Total events in database: {len(all_events)}')
print('')

# Filter for package-related events
package_events = []
for e in all_events:
    # Check if event name contains "package" or params contain package info
    if 'package' in e.event_name.value.lower():
        package_events.append(e)
    elif e.params_json and ('package_id' in str(e.params_json) or 'package_name' in str(e.params_json)):
        package_events.append(e)

if package_events:
    print(f'Found {len(package_events)} package-related events:')
    print('')
    for i, e in enumerate(package_events[-5:], 1):  # Show last 5
        print(f'[{i}] Event: {e.event_name.value}')
        print(f'    Page ID: {e.page_id}')
        print(f'    Timestamp: {e.timestamp}')
        print(f'    Params: {json.dumps(e.params_json, indent=6)}')
        print('')
else:
    print('[INFO] No package-related events found yet.')
    print('')
    print('Recent events (last 5):')
    for i, e in enumerate(all_events[-5:], 1):
        print(f'  [{i}] {e.event_name.value} - {e.page_id} - {e.timestamp}')

# Also check for leads with package metadata
print('')
print('Checking for leads with package metadata...')
try:
    leads = repo.list_leads(db_path, limit=10)
    package_leads = []
    for lead in leads:
        if lead.meta_json and ('package_id' in lead.meta_json or 'package_name' in lead.meta_json):
            package_leads.append(lead)
    
    if package_leads:
        print(f'Found {len(package_leads)} leads with package metadata:')
        for i, lead in enumerate(package_leads[:3], 1):
            print(f'  [{i}] Lead ID: {lead.lead_id}')
            print(f'      Message: {lead.message}')
            print(f'      Meta: {json.dumps(lead.meta_json, indent=6)}')
            print('')
    else:
        print('  No leads with package metadata found.')
except Exception as e:
    print(f'  Could not check leads: {e}')
