"""Check page configuration.

Usage:
    python check_page_config.py
"""

import sys
import os
import json

# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo

if __name__ == "__main__":
    db_path = "acq.db"
    page_id = "p1"
    
    print(f"Checking page configuration: {page_id}")
    print(f"Database: {db_path}")
    print("")
    
    # Get page
    page = repo.get_page(db_path, page_id)
    if not page:
        print(f"ERROR: Page '{page_id}' not found!")
        sys.exit(1)
    
    print(f"Page ID: {page.page_id}")
    print(f"Template ID: {page.template_id}")
    print(f"Client ID: {page.client_id}")
    print("")
    
    # Get client
    client = repo.get_client(db_path, page.client_id)
    if not client:
        print(f"ERROR: Client '{page.client_id}' not found!")
        sys.exit(1)
    
    print(f"Client: {client.client_id}")
    print(f"Business Model: {client.business_model}")
    print("")
    
    # Get packages
    packages = repo.list_packages(db_path, client_id=client.client_id, active=True, limit=10)
    print(f"Packages: {len(packages)}")
    for pkg in packages:
        print(f"  - {pkg.package_id}: {pkg.name} - {pkg.price:.0f} THB")
    print("")
    
    # Check if business_model is fixed_price
    if client.business_model != "fixed_price":
        print(f"WARNING: Client business_model is '{client.business_model}', not 'fixed_price'")
        print("Packages will not be shown unless business_model is 'fixed_price'")
        print("")
        print("To fix:")
        print(f"  Update client business_model to 'fixed_price'")
