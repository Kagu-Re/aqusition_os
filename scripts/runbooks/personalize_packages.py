#!/usr/bin/env python3
"""Add service_focus metadata to packages for page personalization."""

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

print("Current Packages:")
print("=" * 80)
for pkg in packages:
    print(f"  {pkg.package_id}: {pkg.name} (${pkg.price})")
    print(f"    meta_json: {pkg.meta_json}")
print()

# Example: Assign service_focus to packages
# You can customize this based on your package names or other criteria
package_focus_map = {
    # Premium packages (higher price, longer duration)
    # Express packages (shorter duration, quick service)
    # Main packages (standard, no focus)
}

print("To personalize packages:")
print("1. Identify which packages should appear on which pages")
print("2. Update package meta_json with service_focus:")
print()
print("Example:")
print("  from ae import repo")
print("  pkg = repo.get_package('acq.db', 'pkg-relax-60')")
print("  pkg.meta_json['service_focus'] = 'premium'  # or 'express' or None")
print("  repo.update_package('acq.db', pkg)")
print()
