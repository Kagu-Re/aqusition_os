#!/usr/bin/env python3
"""Assign service_focus to packages for page personalization."""

import sys
import os
# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo

db_path = 'acq.db'
client_id = 'test-massage-spa'

# Get all packages
packages = repo.list_packages(db_path, client_id=client_id, active=True, limit=10)

print("Assigning service_focus to packages...")
print("=" * 80)
print()

# Assign service_focus based on package characteristics
# Premium: Higher price or longer duration
# Express: Shorter duration or lower price
# Main: Standard packages

package_assignments = {
    'pkg-deep-90': 'premium',  # Longer duration, higher price
    'pkg-couple-60': 'premium',  # Higher price
    'pkg-relax-60': None,  # Standard/main package
}

for pkg in packages:
    if pkg.package_id in package_assignments:
        new_focus = package_assignments[pkg.package_id]
        current_focus = pkg.meta_json.get('service_focus')
        
        if current_focus != new_focus:
            pkg.meta_json['service_focus'] = new_focus
            repo.update_package(db_path, pkg)
            focus_str = new_focus if new_focus else 'main'
            print(f"[OK] {pkg.package_id}: Assigned service_focus='{focus_str}'")
        else:
            focus_str = current_focus if current_focus else 'main'
            print(f"[SKIP] {pkg.package_id}: Already has service_focus='{focus_str}'")
    else:
        # Keep existing or set to None (main)
        if 'service_focus' not in pkg.meta_json:
            pkg.meta_json['service_focus'] = None
            repo.update_package(db_path, pkg)
            print(f"[OK] {pkg.package_id}: Set service_focus=None (main)")

print()
print("=" * 80)
print("Package assignments complete!")
print()
print("Package distribution:")
print("  Premium page: Will show packages with service_focus='premium'")
print("  Express page: Will show packages with service_focus='express'")
print("  Main page: Will show packages with service_focus=None or missing")
print()
