"""Setup massage client with packages and publish landing page.

Usage:
    python scripts/setup/setup_demo1_client.py
"""

import sys
import os
from datetime import datetime

# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo
from ae.models import Client, ServicePackage, Page
from ae.enums import BusinessModel, Trade
from ae.service import publish_page

if __name__ == "__main__":
    db_path = "acq.db"
    client_id = "test-massage-spa"  # Use massage client instead of demo1
    page_id = "p1"
    
    print(f"Setting up client: {client_id}")
    print(f"Database: {db_path}")
    print("")
    
    # Get or create client
    client = repo.get_client(db_path, client_id)
    if not client:
        print(f"ERROR: Client '{client_id}' not found!")
        print("Please create the client first.")
        sys.exit(1)
    
    print(f"Client: {client.client_name}")
    print(f"Trade: {client.trade}")
    print(f"Business model: {client.business_model}")
    print("")
    
    # Update client business_model to fixed_price if needed
    if client.business_model != BusinessModel.fixed_price:
        print(f"Updating client business_model to 'fixed_price'...")
        updated_client = Client(
            client_id=client.client_id,
            client_name=client.client_name,
            trade=client.trade,
            business_model=BusinessModel.fixed_price,
            geo_country=client.geo_country,
            geo_city=client.geo_city,
            service_area=client.service_area,
            primary_phone=client.primary_phone,
            lead_email=client.lead_email,
            status=client.status,
            hours=getattr(client, "hours", None),
            license_badges=getattr(client, "license_badges", []),
            price_anchor=getattr(client, "price_anchor", None),
            brand_theme=getattr(client, "brand_theme", None),
            notes_internal=getattr(client, "notes_internal", None),
            service_config_json=getattr(client, "service_config_json", {}) or {}
        )
        repo.upsert_client(db_path, updated_client)
        print("[OK] Client business_model updated")
        print("")
    else:
        print("[OK] Client already has business_model = fixed_price")
        print("")
    
    # Ensure packages exist
    packages = repo.list_packages(db_path, client_id=client_id, active=True, limit=10)
    if len(packages) == 0:
        print("Creating packages...")
        from datetime import timezone
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
        
        packages_data = [
            {
                "package_id": "pkg-demo1-relax-60",
                "name": "60-Minute Relaxation Massage",
                "price": 1500.0,
                "duration_min": 60,
                "description": "A relaxing full-body massage to relieve stress and tension",
            },
            {
                "package_id": "pkg-demo1-deep-90",
                "name": "90-Minute Deep Tissue Massage",
                "price": 2200.0,
                "duration_min": 90,
                "description": "Intensive deep tissue massage for muscle recovery",
            },
            {
                "package_id": "pkg-demo1-couple-60",
                "name": "Couples Massage (60 min)",
                "price": 2800.0,
                "duration_min": 60,
                "description": "Enjoy a relaxing massage together",
            }
        ]
        
        for pkg_data in packages_data:
            existing = repo.get_package(db_path, pkg_data['package_id'])
            if not existing:
                pkg = ServicePackage(
                    package_id=pkg_data['package_id'],
                    client_id=client_id,
                    name=pkg_data['name'],
                    price=pkg_data['price'],
                    duration_min=pkg_data['duration_min'],
                    description=pkg_data.get('description', ''),
                    addons=[],
                    active=True,
                    created_at=now,
                    updated_at=now
                )
                repo.create_package(db_path, pkg)
                print(f"  [OK] Created: {pkg_data['name']}")
        print("")
    else:
        print(f"Packages found: {len(packages)}")
        for pkg in packages:
            print(f"  - {pkg.package_id}: {pkg.name} - {pkg.price:.0f} THB")
        print("")
    
    # Add placeholder reviews for demo (GBP sync will replace these later)
    config = getattr(client, "service_config_json", {}) or {}
    if not config.get("reviews"):
        placeholder_reviews = [
            {"quote": "Excellent service, highly recommend!", "author_name": "Sarah M.", "rating": 5, "source": "google"},
            {"quote": "Best massage in Chiang Mai! Will definitely come back.", "author_name": "John D.", "rating": 5, "source": "google"},
        ]
        config["reviews"] = placeholder_reviews
        client.service_config_json = config
        repo.upsert_client(db_path, client, apply_defaults=False)
        print("[OK] Added placeholder reviews for demo")
        print("")
    
    # Ensure page uses correct client
    print(f"Checking page '{page_id}'...")
    page = repo.get_page(db_path, page_id)
    if not page:
        print(f"ERROR: Page '{page_id}' not found!")
        sys.exit(1)
    
    # Ensure page uses correct client and template
    template_id = "service_lp"  # Use service template for massage/spa businesses
    needs_update = False
    
    if page.client_id != client_id:
        print(f"Updating page to use client '{client_id}'...")
        needs_update = True
    
    if page.template_id != template_id:
        print(f"Updating page to use template '{template_id}'...")
        needs_update = True
    
    if needs_update:
        # Get template version
        template = repo.get_template(db_path, template_id)
        if not template:
            print(f"WARNING: Template '{template_id}' not found, keeping current template")
            template_version = page.template_version
        else:
            template_version = template.template_version
        
        updated_page = Page(
            page_id=page.page_id,
            client_id=client_id,
            template_id=template_id,
            template_version=template_version,
            page_slug=page.page_slug,
            page_url=page.page_url,
            page_status=page.page_status,
            content_version=page.content_version,
            service_focus=getattr(page, "service_focus", None),
            locale=page.locale
        )
        repo.upsert_page(db_path, updated_page)
        print(f"[OK] Page updated to use client '{client_id}' and template '{template_id}'")
        print("")
    
    # Publish landing page
    print(f"Publishing landing page: {page_id}...")
    ok, errors = publish_page(db_path, page_id)
    if ok:
        print(f"[OK] Landing page '{page_id}' published successfully!")
        print(f"")
        print(f"Access at: http://localhost:8000/pages/{page_id}")
    else:
        print(f"[ERROR] Failed to publish page '{page_id}'")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
