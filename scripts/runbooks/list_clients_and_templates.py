"""List all clients and templates.

Usage:
    python list_clients_and_templates.py
"""

import sys
import os

# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo

if __name__ == "__main__":
    db_path = "acq.db"
    
    print("=" * 60)
    print("AVAILABLE CLIENTS")
    print("=" * 60)
    print("")
    
    clients = repo.list_clients(db_path, limit=50)
    print(f"Total: {len(clients)} clients")
    print("")
    
    for c in clients:
        print(f"ID: {c.client_id}")
        print(f"  Name: {c.client_name}")
        print(f"  Trade: {c.trade}")
        print(f"  Business Model: {c.business_model}")
        print(f"  Location: {c.geo_city}, {c.geo_country}")
        print(f"  Status: {c.status}")
        
        # Count packages
        packages = repo.list_packages(db_path, client_id=c.client_id, limit=10)
        print(f"  Packages: {len(packages)}")
        if packages:
            for pkg in packages[:3]:
                print(f"    - {pkg.package_id}: {pkg.name} ({pkg.price:.0f} THB)")
            if len(packages) > 3:
                print(f"    ... and {len(packages) - 3} more")
        
        # Count pages
        pages = repo.list_pages(db_path, limit=100)
        client_pages = [p for p in pages if p.client_id == c.client_id]
        print(f"  Pages: {len(client_pages)}")
        if client_pages:
            for page in client_pages[:3]:
                print(f"    - {page.page_id} ({page.page_status})")
            if len(client_pages) > 3:
                print(f"    ... and {len(client_pages) - 3} more")
        
        print("")
    
    print("=" * 60)
    print("AVAILABLE TEMPLATES")
    print("=" * 60)
    print("")
    
    # List templates from database directly
    from ae import db
    db.init_db(db_path)
    conn = db.connect(db_path)
    try:
        template_rows = db.fetchall(conn, "SELECT * FROM templates ORDER BY template_id")
        print(f"Total: {len(template_rows)} templates")
        print("")
        
        for row in template_rows:
            template_id = row["template_id"]
            print(f"ID: {template_id}")
            template_name = row["template_name"] if "template_name" in row.keys() else "N/A"
            template_version = row["template_version"] if "template_version" in row.keys() else "N/A"
            status = row["status"] if "status" in row.keys() else "N/A"
            print(f"  Name: {template_name}")
            print(f"  Version: {template_version}")
            print(f"  Status: {status}")
            
            # Count pages using this template
            pages = repo.list_pages(db_path, limit=100)
            template_pages = [p for p in pages if p.template_id == template_id]
            print(f"  Pages using this template: {len(template_pages)}")
            if template_pages:
                for page in template_pages[:3]:
                    print(f"    - {page.page_id} (client: {page.client_id})")
                if len(template_pages) > 3:
                    print(f"    ... and {len(template_pages) - 3} more")
            
            print("")
    finally:
        conn.close()
    
    print("=" * 60)
    print("ALL PAGES")
    print("=" * 60)
    print("")
    
    pages = repo.list_pages(db_path, limit=50)
    print(f"Total: {len(pages)} pages")
    print("")
    
    for p in pages:
        print(f"ID: {p.page_id}")
        print(f"  Client: {p.client_id}")
        print(f"  Template: {p.template_id}")
        print(f"  Status: {p.page_status}")
        print(f"  URL: {p.page_url}")
        print("")
