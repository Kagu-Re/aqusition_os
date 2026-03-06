#!/usr/bin/env python3
"""Set up availability tracking for packages.

Usage:
    python scripts/setup/setup_availability.py
"""

import sys
import os
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo

db_path = 'acq.db'
client_id = 'test-massage-spa'

print("=" * 80)
print("SETTING UP AVAILABILITY TRACKING")
print("=" * 80)
print()

packages = repo.list_packages(db_path, client_id=client_id, active=True)

print("Current packages:")
for pkg in packages:
    print(f"  {pkg.package_id}: {pkg.name}")
    print(f"    Current meta_json: {pkg.meta_json}")
print()

# Set max_capacity for each package
# This enables availability calculation from Money Board bookings
package_capacities = {
    'pkg-deep-90': 5,      # 5 slots available
    'pkg-couple-60': 3,    # 3 slots available (couples massage, more limited)
    'pkg-relax-60': 8,     # 8 slots available (most popular)
}

print("Setting max_capacity for packages:")
print("-" * 80)

for pkg in packages:
    if pkg.package_id in package_capacities:
        max_cap = package_capacities[pkg.package_id]
        pkg.meta_json['max_capacity'] = max_cap
        repo.update_package(db_path, pkg)
        print(f"  ✅ {pkg.package_id}: Set max_capacity={max_cap}")
    else:
        print(f"  ⚠️  {pkg.package_id}: No capacity configured (skipping)")

print()
print("=" * 80)
print("AVAILABILITY SETUP COMPLETE")
print("=" * 80)
print()
print("How availability works:")
print("  1. Packages now have max_capacity set")
print("  2. When bookings are created in Money Board, availability is calculated:")
print("     available_slots = max_capacity - active_bookings")
print("  3. Active booking states: confirmed, deposit_requested, time_window_set")
print("  4. Display logic:")
print("     - 0 slots: 'Fully booked' (red, disabled)")
print("     - 1 slot: 'Only 1 slot left!' (red, urgent)")
print("     - 2-3 slots: 'Only X slots left' (orange, urgent)")
print("     - 4+ slots: 'Available' (green) or no badge")
print()
print("To test:")
print("  1. Create some BookingRequest records in Money Board")
print("  2. Refresh the premium page to see availability badges")
print()
