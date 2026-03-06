#!/usr/bin/env python3
"""Show content differences between page variations."""

import sys
import os
# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo
from ae.adapters.content_stub import StubContentAdapter

db_path = 'acq.db'
client_id = 'test-massage-spa'

client = repo.get_client(db_path, client_id)
adapter = StubContentAdapter()

page_ids = ['test-massage-spa-main', 'test-massage-spa-premium', 'test-massage-spa-express']

print("=" * 80)
print("CONTENT PERSONALIZATION - PAGE DIFFERENCES")
print("=" * 80)
print()

for page_id in page_ids:
    page = repo.get_page(db_path, page_id)
    payload = adapter.build(page_id, {
        'client': client,
        'page': page,
        'db_path': db_path
    })
    
    focus_label = page.service_focus or "main"
    print(f"{focus_label.upper()} PAGE ({page_id}):")
    print("-" * 80)
    print(f"  Headline: {payload['headline']}")
    print(f"  Subheadline: {payload['subheadline']}")
    print(f"  CTA Primary: {payload['cta_primary']}")
    print(f"  CTA Secondary: {payload['cta_secondary']}")
    print(f"  Amenities: {payload['sections'][0]['items']}")
    print(f"  Testimonials: {payload['sections'][1]['items']}")
    print(f"  FAQ: {payload['sections'][2]['items']}")
    print()

print("=" * 80)
print("PACKAGE PERSONALIZATION")
print("=" * 80)
print()
print("To personalize packages per page, add service_focus to package meta_json:")
print("  - premium packages: meta_json['service_focus'] = 'premium'")
print("  - express packages: meta_json['service_focus'] = 'express'")
print("  - main packages: meta_json['service_focus'] = None or omit")
print()
print("The API will automatically filter packages based on page service_focus.")
print()
