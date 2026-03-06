"""Test the service packages API endpoint."""

import sys
import os
# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae.console_routes_service_packages_public import list_service_packages_public
from fastapi import Request
from unittest.mock import Mock

# Mock request object
class MockRequest:
    def __init__(self):
        self.query_params = Mock()
        self.query_params.get = lambda key, default=None: "acq.db" if key == "db" else default

request = MockRequest()

try:
    result = list_service_packages_public(
        client_id="test-massage-spa",
        request=request,
        active=True,
        limit=50
    )
    print("API Response:")
    print(f"  Count: {result['count']}")
    print(f"  Items: {len(result['items'])}")
    for item in result['items']:
        print(f"    - {item['name']}: ${item['price']} ({item.get('available_slots', 'N/A')} slots)")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
