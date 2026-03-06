#!/usr/bin/env python3
"""Show package service_focus assignments."""

import sys
import os
# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo

db_path = 'acq.db'
client_id = 'test-massage-spa'

packages = repo.list_packages(db_path, client_id=client_id, active=True)

print("Package Service Focus Assignments:")
print("=" * 80)
for pkg in packages:
    focus = pkg.meta_json.get('service_focus', 'main (default)')
    print(f"  {pkg.package_id}:")
    print(f"    Name: {pkg.name}")
    print(f"    Price: ${pkg.price}")
    print(f"    Duration: {pkg.duration_min} min")
    print(f"    service_focus: {focus}")
    print()

print("=" * 80)
print("Package Distribution by Page:")
print("=" * 80)
print()
print("MAIN PAGE will show:")
main_packages = [p for p in packages if p.meta_json.get('service_focus') is None]
for pkg in main_packages:
    print(f"  - {pkg.name} (${pkg.price})")
if not main_packages:
    print("  (no packages assigned to main)")

print()
print("PREMIUM PAGE will show:")
premium_packages = [p for p in packages if p.meta_json.get('service_focus') == 'premium']
for pkg in premium_packages:
    print(f"  - {pkg.name} (${pkg.price})")
if not premium_packages:
    print("  (no packages assigned to premium)")

print()
print("EXPRESS PAGE will show:")
express_packages = [p for p in packages if p.meta_json.get('service_focus') == 'express']
for pkg in express_packages:
    print(f"  - {pkg.name} (${pkg.price})")
if not express_packages:
    print("  (no packages assigned to express)")
