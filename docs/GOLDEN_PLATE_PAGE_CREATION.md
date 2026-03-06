# Golden Plate Page Creation Guide

## Overview

The improved `service_lp` template serves as a "golden plate" (golden template) for creating multiple landing page variations per client. This guide shows how to scale page creation efficiently.

## Template Structure

The golden plate template includes:

1. **Hero Section** - Title, subtitle, CTAs
2. **Features Section** - Three-column grid (Amenities, Why Choose Us, FAQ)
3. **Packages Section** - Dynamic service package display
4. **Footer Section** - Metadata

## Quick Start

### Create Multiple Pages for a Client

```bash
# Create 3 default variations
python create_client_pages.py \
  --db acq.db \
  --client-id test-massage-spa \
  --base-url https://yourdomain.com \
  --publish

# Create custom number of variations
python create_client_pages.py \
  --db acq.db \
  --client-id test-massage-spa \
  --variations 5 \
  --publish
```

### Default Variations Created

1. **Main Landing Page** (`{client-id}-main`)
   - Primary entry point
   - General service overview
   - All packages displayed

2. **Premium Services Page** (`{client-id}-premium`)
   - Focus on premium/high-value packages
   - Service focus: `premium`
   - Can filter packages by price/value

3. **Express Booking Page** (`{client-id}-express`)
   - Quick booking flow
   - Service focus: `express`
   - Emphasizes speed/convenience

## Custom Variations

### Using Python Script

```python
from create_client_pages import create_page_variation

variations = [
    {
        'page_id': 'massage-spa-campaign-feb',
        'slug': 'massage-spa-campaign-feb',
        'url': 'https://yourdomain.com/campaigns/feb',
        'service_focus': 'february_promotion',
        'description': 'February campaign page'
    },
    {
        'page_id': 'massage-spa-valentine',
        'slug': 'massage-spa-valentine',
        'url': 'https://yourdomain.com/special/valentine',
        'service_focus': 'valentine',
        'description': 'Valentine special page'
    }
]

for variation in variations:
    create_page_variation(
        db_path='acq.db',
        client_id='test-massage-spa',
        page_config=variation
    )
```

### Using CLI

```bash
# Create individual pages
python -m ae.cli create-page \
  --db acq.db \
  --page-id test-massage-spa-campaign-1 \
  --client-id test-massage-spa \
  --template-id service_lp \
  --slug test-massage-spa-campaign-1 \
  --url https://yourdomain.com/campaigns/1

# Record validation events
python -c "
from ae import repo, service
from ae.models import EventRecord
from ae.enums import EventName
from datetime import datetime
import uuid

page_id = 'test-massage-spa-campaign-1'
events = [
    EventRecord(
        event_id=f'evt_{uuid.uuid4().hex[:8]}',
        ts=datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
        page_id=page_id,
        event_name=event_name,
        params_json={'test': True}
    )
    for event_name in [EventName.call_click, EventName.quote_submit, EventName.thank_you_view]
]
[repo.insert_event('acq.db', e) for e in events]
print('Events recorded')
"

# Publish
python -m ae.cli publish-page --db acq.db --page-id test-massage-spa-campaign-1
```

## Use Cases

### 1. Campaign-Specific Pages

Create pages for different marketing campaigns:

```python
campaigns = [
    {'name': 'summer', 'slug': 'summer-promo', 'focus': 'summer'},
    {'name': 'winter', 'slug': 'winter-special', 'focus': 'winter'},
    {'name': 'holiday', 'slug': 'holiday-deals', 'focus': 'holiday'}
]

for campaign in campaigns:
    create_page_variation(
        db_path='acq.db',
        client_id='test-massage-spa',
        page_config={
            'page_id': f'test-massage-spa-{campaign["name"]}',
            'slug': campaign['slug'],
            'url': f'https://yourdomain.com/{campaign["slug"]}',
            'service_focus': campaign['focus']
        }
    )
```

### 2. Service-Specific Pages

Create pages focused on specific services:

```python
services = ['massage', 'spa', 'wellness', 'aromatherapy']

for service in services:
    create_page_variation(
        db_path='acq.db',
        client_id='test-massage-spa',
        page_config={
            'page_id': f'test-massage-spa-{service}',
            'slug': f'{service}-services',
            'url': f'https://yourdomain.com/services/{service}',
            'service_focus': service
        }
    )
```

### 3. Geographic Variations

Create pages for different locations:

```python
locations = [
    {'city': 'chiang-mai', 'area': 'old-town'},
    {'city': 'chiang-mai', 'area': 'nimman'},
    {'city': 'bangkok', 'area': 'sukhumvit'}
]

for loc in locations:
    create_page_variation(
        db_path='acq.db',
        client_id='test-massage-spa',
        page_config={
            'page_id': f'test-massage-spa-{loc["city"]}-{loc["area"]}',
            'slug': f'{loc["city"]}-{loc["area"]}',
            'url': f'https://yourdomain.com/{loc["city"]}/{loc["area"]}',
            'service_focus': f'{loc["city"]}_{loc["area"]}'
        }
    )
```

## Batch Operations

### Publish All Pages for a Client

```python
from ae import repo, service

client_id = 'test-massage-spa'
pages = repo.list_pages('acq.db', client_id=client_id)

for page in pages:
    if page.page_status.value == 'draft':
        ok, errors = service.publish_page('acq.db', page.page_id)
        print(f"{'✅' if ok else '❌'} {page.page_id}")
```

### Update All Pages

```python
from ae import repo
from ae.models import Page

client_id = 'test-massage-spa'
pages = repo.list_pages('acq.db', client_id=client_id)

for page in pages:
    # Update content version to trigger republish
    page.content_version += 1
    repo.upsert_page('acq.db', page)
    service.publish_page('acq.db', page.page_id)
```

## Best Practices

1. **Naming Convention**
   - Use consistent naming: `{client-id}-{variation-type}-{identifier}`
   - Examples: `massage-spa-main`, `massage-spa-premium`, `massage-spa-campaign-feb`

2. **URL Structure**
   - Keep URLs consistent: `/{client-slug}/{variation-slug}`
   - Use lowercase, hyphens for separation

3. **Service Focus**
   - Use `service_focus` field to differentiate pages
   - Can be used for filtering packages or customizing content

4. **Validation**
   - Always record validation events before publishing
   - Use the script's `--publish` flag to automate

5. **Versioning**
   - Increment `content_version` when making template changes
   - Republish all pages when template updates

## Output Structure

All pages are published to:

```
exports/static_site/
├── {client-id}-main/
│   └── index.html
├── {client-id}-premium/
│   └── index.html
└── {client-id}-express/
    └── index.html
```

Each page uses the same golden plate template structure but can be customized via:
- Content adapter (different content per page)
- Service focus (filter packages)
- URL parameters (UTM tracking)

## Scaling Tips

1. **Automate Creation**: Use the script for bulk creation
2. **Template Updates**: Update template once, republish all pages
3. **Content Variations**: Use content adapter to customize per page
4. **Package Filtering**: Use `service_focus` to show different packages
5. **A/B Testing**: Create variations for testing different CTAs/content
