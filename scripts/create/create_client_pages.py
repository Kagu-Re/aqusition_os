#!/usr/bin/env python3
"""Create multiple landing pages for a client using the improved template as golden plate.

This script uses the improved service_lp template structure to create multiple
variations of landing pages for a single client.
"""

import sys
import os
# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo, service
from ae.models import Page, EventRecord
from ae.enums import PageStatus, EventName, TemplateStatus
from datetime import datetime
import uuid

def create_page_variation(
    db_path: str,
    client_id: str,
    page_config: dict,
    record_test_events: bool = True
) -> str:
    """Create a landing page variation for a client.
    
    Args:
        db_path: Database path
        client_id: Client ID
        page_config: Dict with:
            - page_id: Unique page ID
            - slug: URL slug
            - url: Full URL
            - service_focus: Optional service focus
            - locale: Locale (default: 'en')
        record_test_events: Whether to record validation events
    
    Returns:
        Page ID
    """
    # Ensure template exists
    template = repo.get_template(db_path, 'service_lp')
    if not template:
        print(f"[INFO] Creating service_lp template...")
        from ae.models import Template
        template = Template(
            template_id='service_lp',
            template_name='Service Business Landing Page',
            template_version='1.0.0',
            cms_schema_version='1.0',
            compatible_events_version='1.0',
            status=TemplateStatus.active
        )
        repo.upsert_template(db_path, template)
    
    # Create page
    page = Page(
        page_id=page_config['page_id'],
        client_id=client_id,
        template_id='service_lp',
        template_version=template.template_version,
        page_slug=page_config['slug'],
        page_url=page_config['url'],
        page_status=PageStatus.draft,
        content_version=1,
        service_focus=page_config.get('service_focus'),
        locale=page_config.get('locale', 'en')
    )
    
    repo.upsert_page(db_path, page)
    print(f"[OK] Created page: {page_config['page_id']}")
    
    # Record test events for validation
    if record_test_events:
        events = [
            EventRecord(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                ts=datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                page_id=page_config['page_id'],
                event_name=event_name,
                params_json={"test": True}
            )
            for event_name in [
                EventName.call_click,
                EventName.quote_submit,
                EventName.thank_you_view
            ]
        ]
        for event in events:
            repo.insert_event(db_path, event)
        print(f"  [OK] Recorded validation events")
    
    return page_config['page_id']


def create_multiple_pages_for_client(
    db_path: str,
    client_id: str,
    base_url: str = "http://localhost",
    variations: list = None
) -> list:
    """Create multiple page variations for a client.
    
    Args:
        db_path: Database path
        client_id: Client ID
        base_url: Base URL for pages
        variations: List of variation configs. If None, creates default variations.
    
    Returns:
        List of created page IDs
    """
    if variations is None:
        # Default variations
        variations = [
            {
                'page_id': f'{client_id}-main',
                'slug': f'{client_id}-main',
                'url': f'{base_url}/{client_id}/main',
                'service_focus': None,
                'description': 'Main landing page'
            },
            {
                'page_id': f'{client_id}-premium',
                'slug': f'{client_id}-premium',
                'url': f'{base_url}/{client_id}/premium',
                'service_focus': 'premium',
                'description': 'Premium services page'
            },
            {
                'page_id': f'{client_id}-express',
                'slug': f'{client_id}-express',
                'url': f'{base_url}/{client_id}/express',
                'service_focus': 'express',
                'description': 'Express booking page'
            }
        ]
    
    created_pages = []
    
    print(f"\n{'='*60}")
    print(f"Creating {len(variations)} page variations for client: {client_id}")
    print(f"{'='*60}\n")
    
    for i, variation in enumerate(variations, 1):
        print(f"[{i}/{len(variations)}] {variation.get('description', variation['page_id'])}")
        page_id = create_page_variation(
            db_path=db_path,
            client_id=client_id,
            page_config={
                'page_id': variation['page_id'],
                'slug': variation['slug'],
                'url': variation['url'],
                'service_focus': variation.get('service_focus'),
                'locale': variation.get('locale', 'en')
            }
        )
        created_pages.append(page_id)
        print()
    
    return created_pages


def publish_all_pages(db_path: str, page_ids: list) -> dict:
    """Publish all created pages.
    
    Returns:
        Dict with page_id -> (success, errors)
    """
    results = {}
    
    print(f"\n{'='*60}")
    print(f"Publishing {len(page_ids)} pages")
    print(f"{'='*60}\n")
    
    for i, page_id in enumerate(page_ids, 1):
        print(f"[{i}/{len(page_ids)}] Publishing: {page_id}")
        ok, errors = service.publish_page(db_path, page_id)
        results[page_id] = (ok, errors)
        if ok:
            print(f"  [OK] Published successfully")
        else:
            print(f"  [ERROR] {errors}")
        print()
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Create multiple landing pages for a client')
    parser.add_argument('--db', default='acq.db', help='Database path')
    parser.add_argument('--client-id', required=True, help='Client ID')
    parser.add_argument('--base-url', default='http://localhost', help='Base URL for pages')
    parser.add_argument('--publish', action='store_true', help='Publish pages after creation')
    parser.add_argument('--variations', type=int, default=3, help='Number of default variations to create')
    
    args = parser.parse_args()
    
    # Create default variations
    variations = [
        {
            'page_id': f'{args.client_id}-main',
            'slug': f'{args.client_id}-main',
            'url': f'{args.base_url}/{args.client_id}/main',
            'service_focus': None,
            'description': 'Main landing page'
        },
        {
            'page_id': f'{args.client_id}-premium',
            'slug': f'{args.client_id}-premium',
            'url': f'{args.base_url}/{args.client_id}/premium',
            'service_focus': 'premium',
            'description': 'Premium services page'
        },
        {
            'page_id': f'{args.client_id}-express',
            'slug': f'{args.client_id}-express',
            'url': f'{args.base_url}/{args.client_id}/express',
            'service_focus': 'express',
            'description': 'Express booking page'
        }
    ][:args.variations]
    
    # Create pages
    page_ids = create_multiple_pages_for_client(
        db_path=args.db,
        client_id=args.client_id,
        base_url=args.base_url,
        variations=variations
    )
    
    # Publish if requested
    if args.publish:
        results = publish_all_pages(args.db, page_ids)
        
        # Summary
        print(f"\n{'='*60}")
        print("Summary")
        print(f"{'='*60}")
        successful = sum(1 for ok, _ in results.values() if ok)
        print(f"Created: {len(page_ids)} pages")
        print(f"Published: {successful}/{len(page_ids)} pages")
        print(f"\nPublished pages:")
        for page_id, (ok, _) in results.items():
            if ok:
                page = repo.get_page(args.db, page_id)
                print(f"  [OK] {page_id}")
                print(f"     URL: {page.page_url}")
                print(f"     File: exports/static_site/{page_id}/index.html")
    else:
        print(f"\n{'='*60}")
        print("Summary")
        print(f"{'='*60}")
        print(f"Created: {len(page_ids)} pages (draft)")
        print(f"\nTo publish:")
        print(f"  python create_client_pages.py --db {args.db} --client-id {args.client_id} --publish")
