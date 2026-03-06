#!/usr/bin/env python3
"""Create a test client with fixed-price business model and service packages."""

import os
import sys
from datetime import datetime

# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae.models import Client, ServicePackage
from ae.enums import Trade, BusinessModel, ClientStatus
from ae import repo

# Determine database path
db_path = 'acq.db' if os.path.exists('acq.db') else 'data/acq.db'
if os.path.dirname(db_path) and not os.path.exists(os.path.dirname(db_path)):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

print("Creating test client...")

# Create client
client = Client(
    client_id='test-massage-spa',
    client_name='Test Massage Spa',
    trade=Trade.massage,
    business_model=BusinessModel.fixed_price,
    geo_country='TH',
    geo_city='chiang mai',
    service_area=['Chiang Mai City'],
    primary_phone='+66-80-000-0000',
    lead_email='test@example.com',
    status=ClientStatus.draft,
    service_config_json={
        'deposit_percentage': 50,
        'features': {
            'service_packages': True,
            'online_booking': True
        }
    }
)

repo.upsert_client(db_path, client)
print(f"[OK] Created client: test-massage-spa (business_model: {client.business_model.value})")

# Create service packages
print("\nCreating service packages...")
now = datetime.utcnow()

packages = [
    ServicePackage(
        package_id='pkg-relax-60',
        client_id='test-massage-spa',
        name='60-Minute Relaxation Massage',
        price=1500.0,
        duration_min=60,
        addons=['Aromatherapy', 'Hot stones'],
        active=True,
        meta_json={},
        created_at=now,
        updated_at=now
    ),
    ServicePackage(
        package_id='pkg-deep-90',
        client_id='test-massage-spa',
        name='90-Minute Deep Tissue Massage',
        price=2200.0,
        duration_min=90,
        addons=['Hot stones'],
        active=True,
        meta_json={},
        created_at=now,
        updated_at=now
    ),
    ServicePackage(
        package_id='pkg-couple-60',
        client_id='test-massage-spa',
        name='Couples Massage (60 min)',
        price=2800.0,
        duration_min=60,
        addons=['Champagne', 'Private room'],
        active=True,
        meta_json={},
        created_at=now,
        updated_at=now
    ),
]

for pkg in packages:
    repo.create_package(db_path, pkg)
    print(f"  [OK] {pkg.name}: ${pkg.price} ({pkg.duration_min} min)")

# Verify
print("\nVerifying...")
client = repo.get_client(db_path, 'test-massage-spa')
packages = repo.list_packages(db_path, client_id='test-massage-spa', active=True)

print(f"\n[OK] Client: {client.client_name}")
print(f"  Business Model: {client.business_model.value}")
print(f"  Trade: {client.trade.value}")
print(f"  Service Packages: {len(packages)}")

print("\n[OK] Test client created successfully!")
print("\nNext steps:")
print("  1. Create a page: python -m ae.cli create-page --db acq.db --page-id test-page --client-id test-massage-spa --template-id trade_lp --slug test-massage --url http://localhost/test")
print("  2. Publish page: python -m ae.cli publish-page --db acq.db --page-id test-page")
print("  3. View: exports/static_site/test-page/index.html")
