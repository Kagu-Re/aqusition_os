"""Fix client business model to show packages.

Usage:
    python fix_client_business_model.py
"""

import sys
import os

# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo
from ae.models import Client
from ae.enums import BusinessModel

if __name__ == "__main__":
    db_path = "acq.db"
    client_id = "demo1"
    
    print(f"Updating client business model: {client_id}")
    print(f"Database: {db_path}")
    print("")
    
    # Get client
    client = repo.get_client(db_path, client_id)
    if not client:
        print(f"ERROR: Client '{client_id}' not found!")
        sys.exit(1)
    
    print(f"Current business_model: {client.business_model}")
    print("")
    
    # Update business model
    print("Updating business_model to 'fixed_price'...")
    
    # Create updated client with fixed_price business model
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
    
    print("[OK] Client business_model updated to 'fixed_price'")
    print("")
    print("Next step: Republish the landing page")
    print("  python publish_landing_page.py p1")
