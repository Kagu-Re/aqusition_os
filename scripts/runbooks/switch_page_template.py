"""Switch page template to service_lp.

Usage:
    python switch_page_template.py
"""

import sys
import os

# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo
from ae.models import Page
from ae.service import publish_page

if __name__ == "__main__":
    db_path = "acq.db"
    page_id = "p1"
    new_template_id = "service_lp"
    
    print(f"Switching page '{page_id}' to template '{new_template_id}'")
    print(f"Database: {db_path}")
    print("")
    
    # Get page
    page = repo.get_page(db_path, page_id)
    if not page:
        print(f"ERROR: Page '{page_id}' not found!")
        sys.exit(1)
    
    print(f"Current template: {page.template_id}")
    print(f"New template: {new_template_id}")
    print("")
    
    # Check if template exists
    template = repo.get_template(db_path, new_template_id)
    if not template:
        print(f"ERROR: Template '{new_template_id}' not found!")
        sys.exit(1)
    
    print(f"Template found: {template.template_name}")
    print(f"Version: {template.template_version}")
    print("")
    
    # Update page
    updated_page = Page(
        page_id=page.page_id,
        client_id=page.client_id,
        template_id=new_template_id,
        template_version=template.template_version,
        page_slug=page.page_slug,
        page_url=page.page_url,
        page_status=page.page_status,
        content_version=page.content_version,
        service_focus=getattr(page, "service_focus", None),
        locale=page.locale
    )
    
    repo.upsert_page(db_path, updated_page)
    print(f"[OK] Page '{page_id}' updated to use template '{new_template_id}'")
    print("")
    
    # Republish page
    print(f"Republishing page '{page_id}'...")
    ok, errors = publish_page(db_path, page_id)
    if ok:
        print(f"[OK] Page '{page_id}' republished successfully!")
        print(f"")
        print(f"Access at: http://localhost:8000/pages/{page_id}")
    else:
        print(f"[ERROR] Failed to republish page '{page_id}'")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
