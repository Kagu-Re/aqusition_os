#!/usr/bin/env python3
"""Show all landing page URLs for inspection."""

import sys
import os
from pathlib import Path

# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo

db_path = 'acq.db'

# Get all pages
all_pages = repo.list_pages(db_path, limit=100)

# Check which pages are published (have files)
static_dir = Path('exports/static_site')
published_pages = []
unpublished_pages = []

for page in all_pages:
    page_file = static_dir / page.page_id / 'index.html'
    if page_file.exists():
        published_pages.append(page)
    else:
        unpublished_pages.append(page)

print("=" * 80)
print("LANDING PAGE URLs FOR INSPECTION")
print("=" * 80)
print()

if published_pages:
    print(f"PUBLISHED PAGES ({len(published_pages)}):")
    print("-" * 80)
    print()
    print("To view these pages, start the server:")
    print("  serve_pages.bat")
    print()
    print("Then visit:")
    print()
    
    for i, page in enumerate(published_pages, 1):
        url = f"http://localhost:8080/{page.page_id}/index.html"
        print(f"  [{i}] {page.page_id}")
        print(f"      Client: {page.client_id}")
        print(f"      Status: {page.page_status.value}")
        print(f"      Template: {page.template_id}")
        print(f"      URL: {url}")
        if page.service_focus:
            print(f"      Focus: {page.service_focus}")
        print()
    
    print()
    print("Quick access URLs:")
    print("-" * 80)
    for page in published_pages:
        print(f"  http://localhost:8080/{page.page_id}/index.html")
    print()

if unpublished_pages:
    print(f"UNPUBLISHED PAGES ({len(unpublished_pages)}):")
    print("-" * 80)
    print()
    for i, page in enumerate(unpublished_pages, 1):
        print(f"  [{i}] {page.page_id}")
        print(f"      Client: {page.client_id}")
        print(f"      Status: {page.page_status.value}")
        print(f"      Template: {page.template_id}")
        print(f"      Database URL: {page.page_url}")
        print(f"      Note: Not yet published (no file at exports/static_site/{page.page_id}/index.html)")
        print()

print("=" * 80)
print("TO START THE SERVER:")
print("=" * 80)
print("  serve_pages.bat")
print()
print("Or manually:")
print("  cd exports\\static_site")
print("  python -m http.server 8080")
print()
