#!/usr/bin/env python3
"""Test package filtering by service_focus."""

import sys
import os
# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae.console_routes_service_packages_public import list_service_packages_public
from fastapi import Request
from unittest.mock import Mock

class MockRequest:
    def __init__(self):
        self.query_params = Mock()
        self.query_params.get = lambda key, default=None: "acq.db" if key == "db" else default

request = MockRequest()

print("Testing Package Filtering by service_focus")
print("=" * 80)
print()

# Test main page (service_focus=None)
print("MAIN PAGE (service_focus=None):")
try:
    result = list_service_packages_public(
        client_id="test-massage-spa",
        request=request,
        active=True,
        limit=50,
        service_focus=None
    )
    print(f"  Found {result['count']} packages:")
    for item in result['items']:
        print(f"    - {item['name']}: ${item['price']}")
except Exception as e:
    print(f"  Error: {e}")

print()

# Test premium page
print("PREMIUM PAGE (service_focus='premium'):")
try:
    result = list_service_packages_public(
        client_id="test-massage-spa",
        request=request,
        active=True,
        limit=50,
        service_focus="premium"
    )
    print(f"  Found {result['count']} packages:")
    for item in result['items']:
        print(f"    - {item['name']}: ${item['price']}")
except Exception as e:
    print(f"  Error: {e}")

print()

# Test express page
print("EXPRESS PAGE (service_focus='express'):")
try:
    result = list_service_packages_public(
        client_id="test-massage-spa",
        request=request,
        active=True,
        limit=50,
        service_focus="express"
    )
    print(f"  Found {result['count']} packages:")
    for item in result['items']:
        print(f"    - {item['name']}: ${item['price']}")
except Exception as e:
    print(f"  Error: {e}")
