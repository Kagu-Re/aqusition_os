"""Publish landing page with packages.

Usage:
    python publish_landing_page.py [page_id]
"""

import sys
import os

# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo
from ae.service import publish_page

if __name__ == "__main__":
    db_path = "acq.db"
    page_id = sys.argv[1] if len(sys.argv) > 1 else "p1"
    
    print(f"Publishing landing page: {page_id}")
    print(f"Database: {db_path}")
    print("")
    
    # Check if page exists
    page = repo.get_page(db_path, page_id)
    if not page:
        print(f"ERROR: Page '{page_id}' not found!")
        print("")
        print("Available pages:")
        pages = repo.list_pages(db_path, limit=20)
        for p in pages:
            print(f"  - {p.page_id}")
        sys.exit(1)
    
    print(f"Page found: {page_id}")
    print(f"Client ID: {page.client_id}")
    print(f"Template ID: {page.template_id}")
    print("")
    
    # Check packages
    packages = repo.list_packages(db_path, client_id=page.client_id, active=True, limit=10)
    print(f"Packages found: {len(packages)}")
    for pkg in packages:
        print(f"  - {pkg.package_id}: {pkg.name} - {pkg.price:.0f} THB")
    print("")
    
    # Publish page
    print("Publishing...")
    ok, errors = publish_page(db_path, page_id)
    
    if ok:
        print(f"[OK] Page '{page_id}' published successfully!")
        print(f"")
        print(f"Access at: http://localhost:8000/pages/{page_id}")
    else:
        print(f"[ERROR] Failed to publish page '{page_id}'")
        print("Errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
