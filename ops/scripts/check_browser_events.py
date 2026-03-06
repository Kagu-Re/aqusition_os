#!/usr/bin/env python3
"""Quick script to check for browser-recorded events."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from ae import repo
import json

db_path = "acq.db"
page_id = "p1"

events = repo.list_events(db_path, page_id)
browser_events = [e for e in events if 'url' in e.params_json or 'referrer' in e.params_json]
cli_events = [e for e in events if 'url' not in e.params_json and 'referrer' not in e.params_json]

print(f"Total events: {len(events)}")
print(f"Browser events: {len(browser_events)}")
print(f"CLI events: {len(cli_events)}")
print()

if browser_events:
    print("Recent browser events:")
    for e in sorted(browser_events, key=lambda x: x.timestamp, reverse=True)[:5]:
        print(f"  [OK] {e.event_name.value}")
        print(f"     Time: {e.timestamp}")
        if 'url' in e.params_json:
            url = e.params_json['url']
            print(f"     URL: {url[:70]}...")
        print()
