"""Test page content differences."""

import sys
import os
# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo
from ae.adapters.content_stub import StubContentAdapter

db_path = 'acq.db'
client_id = 'test-massage-spa'

client = repo.get_client(db_path, client_id)
adapter = StubContentAdapter()

page_ids = ['test-massage-spa-main', 'test-massage-spa-premium', 'test-massage-spa-express']

print("Current Content (all pages identical):")
print("=" * 80)

for page_id in page_ids:
    page = repo.get_page(db_path, page_id)
    payload = adapter.build(page_id, {
        'client': client,
        'page': page,
        'db_path': db_path
    })
    
    print(f"\n{page_id}:")
    print(f"  service_focus: {page.service_focus}")
    print(f"  headline: {payload['headline']}")
    print(f"  subheadline: {payload['subheadline']}")
    print(f"  cta_primary: {payload['cta_primary']}")
    print(f"  amenities: {payload['sections'][0]['items'][:2]}")
