#!/usr/bin/env python3
"""List all pages for a client."""

import sys
import os
# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo

db_path = 'acq.db'
client_id = 'test-massage-spa'

all_pages = repo.list_pages(db_path)
pages = [p for p in all_pages if p.client_id == client_id]

print(f'\n[OK] Found {len(pages)} pages for client: {client_id}\n')

for i, page in enumerate(pages, 1):
    print(f'  [{i}] {page.page_id}')
    print(f'      Status: {page.page_status.value}')
    print(f'      URL: {page.page_url}')
    print(f'      Slug: {page.page_slug}')
    print(f'      Template: {page.template_id}')
    if page.service_focus:
        print(f'      Focus: {page.service_focus}')
    print(f'      File: exports/static_site/{page.page_id}/index.html')
    print()
