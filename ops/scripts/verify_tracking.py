#!/usr/bin/env python3
"""Verify that event tracking is correctly integrated with the database.

This script:
1. Checks HTML has tracking JavaScript
2. Verifies API endpoint is accessible
3. Tests API endpoint directly
4. Distinguishes browser events from CLI events
5. Validates event flow end-to-end
"""

import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from ae import repo
from ae.models import EventRecord


def check_html_tracking(page_id: str, exports_dir: str = "exports/static_site") -> bool:
    """Check if HTML file has tracking JavaScript."""
    html_path = Path(exports_dir) / page_id / "index.html"
    
    if not html_path.exists():
        print(f"❌ HTML file not found: {html_path}")
        return False
    
    content = html_path.read_text(encoding="utf-8")
    
    checks = [
        ("Acquisition Engine Tracking" in content, "Tracking script comment"),
        ("trackEvent" in content, "trackEvent function"),
        (f'PAGE_ID = "{page_id}"' in content or f"PAGE_ID = '{page_id}'" in content, "Page ID configured"),
        ("/v1/event" in content, "API endpoint reference"),
    ]
    
    all_pass = True
    print(f"\n📄 Checking HTML: {html_path}")
    for passed, desc in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {desc}")
        if not passed:
            all_pass = False
    
    return all_pass


def check_api_endpoint(api_url: str = "http://localhost:8001") -> bool:
    """Check if API endpoint is accessible."""
    import urllib.request
    import urllib.error
    
    try:
        health_url = f"{api_url}/health"
        req = urllib.request.Request(health_url)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                print(f"\n🌐 API endpoint accessible: {api_url}")
                return True
    except Exception as e:
        print(f"\n❌ API endpoint not accessible: {api_url}")
        print(f"   Error: {e}")
        print(f"   Make sure public API is running: python -m ae.public_api")
        return False
    
    return False


def test_api_event(api_url: str, db_path: str, page_id: str) -> bool:
    """Test API endpoint by sending a test event."""
    import urllib.request
    import urllib.error
    import urllib.parse
    
    try:
        event_url = f"{api_url}/v1/event?db={urllib.parse.quote(db_path)}"
        payload = {
            "page_id": page_id,
            "event_name": "call_click",
            "params": {
                "test": "verify_tracking_script",
                "timestamp": datetime.utcnow().isoformat(),
                "source": "automated_test"
            }
        }
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            event_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                result = json.loads(response.read().decode("utf-8"))
                print(f"\n✅ API test event recorded: {result.get('event_id')}")
                return True
            else:
                print(f"\n❌ API returned status {response.status}")
                return False
    except Exception as e:
        print(f"\n❌ API test failed: {e}")
        return False


def analyze_events(db_path: str, page_id: str) -> Dict[str, Any]:
    """Analyze events in database and categorize by source."""
    events = repo.list_events(db_path, page_id)
    
    browser_events = []
    cli_events = []
    api_test_events = []
    
    for e in events:
        params = e.params_json
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except:
                params = {}
        
        # Check for browser indicators
        if "url" in params or "referrer" in params:
            browser_events.append(e)
        elif params.get("test") == "verify_tracking_script":
            api_test_events.append(e)
        else:
            cli_events.append(e)
    
    # Count by event type
    event_counts = {}
    for e in events:
        event_counts[e.event_name.value] = event_counts.get(e.event_name.value, 0) + 1
    
    return {
        "total": len(events),
        "browser": len(browser_events),
        "cli": len(cli_events),
        "api_test": len(api_test_events),
        "by_type": event_counts,
        "browser_events": browser_events,
        "cli_events": cli_events,
        "api_test_events": api_test_events
    }


def check_validation(db_path: str, page_id: str) -> bool:
    """Check if page has validated events."""
    return repo.has_validated_events(db_path, page_id)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify event tracking integration")
    parser.add_argument("--db", default="acq.db", help="Database path")
    parser.add_argument("--page-id", default="p1", help="Page ID to check")
    parser.add_argument("--api-url", default="http://localhost:8001", help="Public API URL")
    parser.add_argument("--skip-api-test", action="store_true", help="Skip API endpoint test")
    args = parser.parse_args()
    
    print("=" * 60)
    print("Event Tracking Verification")
    print("=" * 60)
    print(f"Database: {args.db}")
    print(f"Page ID: {args.page_id}")
    print(f"API URL: {args.api_url}")
    print()
    
    results = {
        "html_tracking": False,
        "api_accessible": False,
        "api_test": False,
        "validation": False
    }
    
    # Step 1: Check HTML
    results["html_tracking"] = check_html_tracking(args.page_id)
    
    # Step 2: Check API
    results["api_accessible"] = check_api_endpoint(args.api_url)
    
    # Step 3: Test API (if accessible)
    if results["api_accessible"] and not args.skip_api_test:
        results["api_test"] = test_api_event(args.api_url, args.db, args.page_id)
    
    # Step 4: Analyze events
    print("\n" + "=" * 60)
    print("Event Analysis")
    print("=" * 60)
    analysis = analyze_events(args.db, args.page_id)
    
    print(f"\n📊 Total events: {analysis['total']}")
    print(f"   Browser-recorded: {analysis['browser']}")
    print(f"   CLI-recorded: {analysis['cli']}")
    print(f"   API test events: {analysis['api_test']}")
    
    if analysis['by_type']:
        print(f"\n📈 Events by type:")
        for event_type, count in sorted(analysis['by_type'].items()):
            print(f"   {event_type}: {count}")
    
    # Show recent browser events
    if analysis['browser_events']:
        print(f"\n🌐 Recent browser events:")
        for e in sorted(analysis['browser_events'], key=lambda x: x.timestamp, reverse=True)[:3]:
            params = e.params_json
            url = params.get('url', 'N/A')
            print(f"   - {e.event_name.value} at {e.timestamp}")
            print(f"     URL: {url[:60]}...")
    
    # Step 5: Check validation
    print("\n" + "=" * 60)
    print("Validation Check")
    print("=" * 60)
    results["validation"] = check_validation(args.db, args.page_id)
    
    if results["validation"]:
        print("✅ Page has validated events (all 3 required events exist)")
    else:
        print("❌ Page validation failed (missing required events)")
        print("   Required: call_click, quote_submit, thank_you_view")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    all_pass = all([
        results["html_tracking"],
        results["api_accessible"],
        results["validation"]
    ])
    
    for check, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}")
    
    if all_pass:
        print("\n✅ All checks passed! Tracking is correctly integrated.")
        return 0
    else:
        print("\n⚠️  Some checks failed. See details above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
