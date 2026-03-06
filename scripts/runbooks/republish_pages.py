#!/usr/bin/env python3
"""Republish pages to apply content personalization changes."""

import sys
import os
# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo, service

db_path = 'acq.db'
page_ids = ['test-massage-spa-main', 'test-massage-spa-premium', 'test-massage-spa-express']

print("Republishing pages with personalized content...")
print("=" * 80)

for page_id in page_ids:
    print(f"\nRepublishing: {page_id}")
    ok, errors = service.publish_page(db_path, page_id)
    if ok:
        print(f"  [OK] Published successfully")
        page = repo.get_page(db_path, page_id)
        print(f"  File: exports/static_site/{page_id}/index.html")
    else:
        print(f"  [ERROR] {errors}")

print("\n" + "=" * 80)
print("Republishing complete!")
print("\nTo view pages:")
print("  1. Start server: serve_pages.bat")
print("  2. Visit:")
for page_id in page_ids:
    print(f"     http://localhost:8080/{page_id}/index.html")
