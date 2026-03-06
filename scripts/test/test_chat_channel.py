#!/usr/bin/env python3
"""Test the chat channel API endpoint."""

import sys
import os
# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

try:
    import requests
except ImportError:
    print('[ERROR] requests library not installed. Install with: pip install requests')
    sys.exit(1)

response = requests.get('http://localhost:8001/v1/chat/channel?client_id=test-massage-spa&db=acq.db')

print('[OK] Chat channel API test:')
print(f'   Status: {response.status_code}')

if response.status_code == 200:
    data = response.json()
    print(f'   Channel ID: {data.get("channel_id", "N/A")}')
    print(f'   Provider: {data.get("provider", "N/A")}')
    print(f'   Chat URL: {data.get("chat_url", "N/A")}')
    print('')
    print('[OK] Chat channel is accessible via public API!')
else:
    print(f'   Error: {response.text}')
    print('')
    print('[ERROR] Chat channel API test failed')
