"""Setup packages for demo1 client.

Usage:
    python scripts/setup/setup_packages_for_demo1.py
"""

import sys
import os

# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo
from ae.models import ServicePackage

if __name__ == "__main__":
    db_path = "acq.db"
    client_id = "demo1"
    
    print(f"Setting up packages for client: {client_id}")
    print(f"Database: {db_path}")
    print("")
    
    # Get all packages
    packages = repo.list_packages(db_path, limit=20)
    
    print(f"Found {len(packages)} packages")
    print("")
    
    # Update each package to belong to demo1
    updated_count = 0
    for pkg in packages:
        print(f"Updating {pkg.package_id}...")
        try:
            repo.update_package(db_path, pkg.package_id, client_id=client_id)
            print(f"  [OK] Updated to client_id: {client_id}")
            updated_count += 1
        except Exception as e:
            print(f"  [ERROR] {e}")
    
    print("")
    print(f"[OK] Updated {updated_count} packages to client_id: {client_id}")
    print("")
    
    # Verify
    demo1_packages = repo.list_packages(db_path, client_id=client_id, active=True, limit=10)
    print(f"Packages for {client_id}:")
    for pkg in demo1_packages:
        print(f"  - {pkg.package_id}: {pkg.name} - {pkg.price:.0f} THB")
