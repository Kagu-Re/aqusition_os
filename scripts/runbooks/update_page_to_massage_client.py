"""Update page p1 to use test-massage-spa client.

Usage:
    python update_page_to_massage_client.py
"""

import sys
import os

# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo
from ae.models import Page

if __name__ == "__main__":
    db_path = "acq.db"
    page_id = "p1"
    new_client_id = "test-massage-spa"
    
    print(f"Updating page '{page_id}' to use client '{new_client_id}'")
    print(f"Database: {db_path}")
    print("")
    
    # Get page
    page = repo.get_page(db_path, page_id)
    if not page:
        print(f"ERROR: Page '{page_id}' not found!")
        sys.exit(1)
    
    print(f"Current client_id: {page.client_id}")
    print(f"New client_id: {new_client_id}")
    print("")
    
    # Get new client
    new_client = repo.get_client(db_path, new_client_id)
    if not new_client:
        print(f"ERROR: Client '{new_client_id}' not found!")
        sys.exit(1)
    
    print(f"New client: {new_client.client_name}")
    print(f"Trade: {new_client.trade}")
    print("")
    
    # Update page
    updated_page = Page(
        page_id=page.page_id,
        client_id=new_client_id,
        template_id=page.template_id,
        template_version=page.template_version,
        page_slug=page.page_slug,
        page_url=page.page_url,
        page_status=page.page_status,
        content_version=page.content_version,
        service_focus=getattr(page, "service_focus", None),
        locale=page.locale
    )
    
    repo.upsert_page(db_path, updated_page)
    print(f"[OK] Page '{page_id}' updated to use client '{new_client_id}'")
    print("")
    
    # Check packages for new client
    packages = repo.list_packages(db_path, client_id=new_client_id, active=True, limit=10)
    print(f"Packages for {new_client_id}: {len(packages)}")
    for pkg in packages:
        print(f"  - {pkg.package_id}: {pkg.name} - {pkg.price:.0f} THB")
    print("")
    
    if len(packages) == 0:
        print("WARNING: No packages found for this client!")
        print("Packages will need to be created or moved to this client.")
    else:
        print("Next step: Republish the landing page")
        print("  python publish_landing_page.py p1")
