"""Create packages for demo1 client.

Usage:
    python create_packages_for_demo1.py
"""

import sys
import os

# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo
from ae.models import ServicePackage
from datetime import datetime

if __name__ == "__main__":
    db_path = "acq.db"
    client_id = "demo1"
    
    print(f"Creating packages for client: {client_id}")
    print(f"Database: {db_path}")
    print("")
    
    # Packages to create
    packages_data = [
        {
            "package_id": "pkg-demo1-relax-60",
            "name": "60-Minute Relaxation Massage",
            "price": 1500.0,
            "duration_min": 60,
            "description": "A relaxing full-body massage to relieve stress and tension",
            "addons": []
        },
        {
            "package_id": "pkg-demo1-deep-90",
            "name": "90-Minute Deep Tissue Massage",
            "price": 2200.0,
            "duration_min": 90,
            "description": "Intensive deep tissue massage for muscle recovery",
            "addons": []
        },
        {
            "package_id": "pkg-demo1-couple-60",
            "name": "Couples Massage (60 min)",
            "price": 2800.0,
            "duration_min": 60,
            "description": "Enjoy a relaxing massage together",
            "addons": []
        }
    ]
    
    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    
    created_count = 0
    for pkg_data in packages_data:
        print(f"Creating {pkg_data['package_id']}...")
        try:
            # Check if exists
            existing = repo.get_package(db_path, pkg_data['package_id'])
            if existing:
                print(f"  [SKIP] Package already exists")
                continue
            
            # Create package
            pkg = ServicePackage(
                package_id=pkg_data['package_id'],
                client_id=client_id,
                name=pkg_data['name'],
                price=pkg_data['price'],
                duration_min=pkg_data['duration_min'],
                description=pkg_data.get('description', ''),
                addons=pkg_data.get('addons', []),
                active=True,
                created_at=now,
                updated_at=now
            )
            
            repo.create_package(db_path, pkg)
            print(f"  [OK] Created: {pkg_data['name']} - {pkg_data['price']:.0f} THB")
            created_count += 1
        except Exception as e:
            print(f"  [ERROR] {e}")
    
    print("")
    print(f"[OK] Created {created_count} packages for {client_id}")
    print("")
    
    # Verify
    demo1_packages = repo.list_packages(db_path, client_id=client_id, active=True, limit=10)
    print(f"Packages for {client_id}:")
    for pkg in demo1_packages:
        print(f"  - {pkg.package_id}: {pkg.name} - {pkg.price:.0f} THB")
