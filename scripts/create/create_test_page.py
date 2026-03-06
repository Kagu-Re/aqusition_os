#!/usr/bin/env python3
"""Create and publish a test landing page for the test-massage-spa client."""

import os
import sys
from datetime import datetime

# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae.models import Page, EventRecord
from ae.enums import PageStatus, EventName
from ae import repo
from ae import service

db_path = 'acq.db'

print("Creating landing page...")

# Create page
page = Page(
    page_id='test-massage-page',
    client_id='test-massage-spa',
    template_id='trade_lp',
    template_version='1.0.0',
    page_slug='test-massage-spa',
    page_url='http://localhost/test-massage-spa',
    page_status=PageStatus.draft,
    content_version=1,
    locale='en'
)

repo.upsert_page(db_path, page)
print(f"[OK] Created page: test-massage-page")

# Record test events (required for validation)
print("\nRecording test events...")
events = [
    EventRecord(
        event_id=f"evt_{i}",
        ts=datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        page_id='test-massage-page',
        event_name=event_name,
        params_json={"test": True}
    )
    for i, event_name in enumerate([
        EventName.call_click,
        EventName.quote_submit,
        EventName.thank_you_view
    ])
]

for event in events:
    repo.insert_event(db_path, event)
    print(f"  [OK] Recorded: {event.event_name.value}")

# Validate page
print("\nValidating page...")
ok, errors = service.validate_page(db_path, 'test-massage-page')
if ok:
    print("[OK] Validation passed")
else:
    print(f"[ERROR] Validation failed: {errors}")
    sys.exit(1)

# Publish page
print("\nPublishing page...")
ok, errors = service.publish_page(db_path, 'test-massage-page')
if ok:
    print("[OK] Page published successfully")
    print(f"\nPublished to: exports/static_site/test-massage-page/index.html")
    print("\nTo view:")
    print("  1. Open: exports/static_site/test-massage-page/index.html")
    print("  2. Or serve: cd exports/static_site/test-massage-page && python -m http.server 8080")
    print("  3. Then visit: http://localhost:8080/index.html")
else:
    print(f"[ERROR] Publishing failed: {errors}")
    sys.exit(1)
