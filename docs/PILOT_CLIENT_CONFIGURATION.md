# Pilot Checklist: Client Configuration

This guide walks through configuring a new client for the Acquisition Engine pilot.

## Overview

Client configuration is the first step in the pilot checklist. A properly configured client enables:
- Landing page creation and publishing
- Attribution tracking (UTM, QR codes)
- Lead intake and routing
- Chat automation
- Booking and payment workflows
- Reporting and analytics

## Step 1: Gather Client Information

Before starting, collect the following information:

### Required Information
- **Client ID** (slug): Stable identifier (e.g., `plumber-cm-oldtown`, `barber-sydney-cbd`)
- **Client Name**: Display name (e.g., "CM Oldtown Plumbing", "Sydney CBD Barber")
- **Trade**: One of: `plumber`, `electrician`, `roofing`, `pest_control`, `hvac`
- **Geo Country**: ISO country code (e.g., `au`, `th`, `us`)
- **Geo City**: City name (e.g., `brisbane`, `chiang mai`, `sydney`)
- **Service Area**: List of areas served (e.g., `["Brisbane North", "Brisbane CBD"]`)
- **Primary Phone**: Contact phone (e.g., `+61-400-000-000`)
- **Lead Email**: Email for lead notifications (e.g., `leads@example.com`)

### Optional Information
- **Hours**: Business hours (e.g., `Mon-Fri 8am-6pm`)
- **License Badges**: List of certifications/licenses
- **Price Anchor**: Typical service price range
- **Brand Theme**: Branding notes
- **Internal Notes**: Operator notes

## Step 2: Create Client Record

### Using CLI (Recommended)

```bash
# Set PYTHONPATH or use wrapper script
set PYTHONPATH=src  # Windows
# export PYTHONPATH=src  # Linux/macOS

# Create client
python -m ae.cli create-client \
  --db acq.db \
  --client-id plumber-cm-oldtown \
  --name "CM Oldtown Plumbing" \
  --trade plumber \
  --city "chiang mai" \
  --phone "+66-80-000-0000" \
  --email "leads@example.com" \
  --service-area "Chiang Mai Old Town" \
  --service-area "Chiang Mai City"
```

### Using Console UI

1. Start console: `python -m ae.cli serve-console`
2. Navigate to: `http://localhost:8000/console/clients`
3. Use the client creation form

### Using Python API

```python
from ae import repo
from ae.models import Client
from ae.enums import Trade

client = Client(
    client_id="plumber-cm-oldtown",
    client_name="CM Oldtown Plumbing",
    trade=Trade.plumber,
    geo_country="th",
    geo_city="chiang mai",
    service_area=["Chiang Mai Old Town", "Chiang Mai City"],
    primary_phone="+66-80-000-0000",
    lead_email="leads@example.com",
    status="draft",  # or "live" when ready
)

repo.upsert_client("acq.db", client)
```

## Step 3: Initialize Onboarding Templates

Onboarding templates define:
- **UTM Policy**: How to structure UTM parameters for attribution
- **Naming Policy**: Conventions for IDs and slugs
- **Event Map**: What events to track and how

### Using CLI

```bash
python -m ae.cli onboarding-init \
  --db acq.db \
  --client-id plumber-cm-oldtown
```

This creates default templates that you can customize.

### Using Console UI

1. Navigate to: `http://localhost:8000/console/onboarding?client_id=plumber-cm-oldtown`
2. Review and customize the templates
3. Click "Save" to persist changes

### Customizing Templates

You can edit templates via:
- Console UI: `/console/onboarding`
- CLI: Direct database access
- Python API: `repo.upsert_onboarding_template()`

## Step 4: Verify Client Configuration

### Check Client Record

```bash
# List all clients
python -m ae.cli list-clients --db acq.db

# Get specific client details
python -m ae.cli get-client --db acq.db --client-id plumber-cm-oldtown
```

### Verify Onboarding Templates

```bash
# Check templates exist
python -m ae.cli onboarding-init --db acq.db --client-id plumber-cm-oldtown
# Should show: "ok: ensured 3 templates for plumber-cm-oldtown"
```

### Generate Onboarding Pack

```bash
python -m ae.cli generate-onboarding \
  --db acq.db \
  --client-id plumber-cm-oldtown \
  --out-root clients
```

This generates markdown files in `clients/plumber-cm-oldtown/` with:
- UTM policy
- Naming conventions
- Event map
- First 7 days checklist

## Step 5: Next Steps

Once client is configured, proceed to:

1. **Create Template** (if not using existing)
   ```bash
   python -m ae.cli create-template \
     --db acq.db \
     --template-id trade_lp \
     --version 1.0.0 \
     --cms-schema 1.0 \
     --events 1.0
   ```

2. **Create Landing Page**
   ```bash
   python -m ae.cli create-page \
     --db acq.db \
     --page-id p-plumber-cm-oldtown-v1 \
     --client-id plumber-cm-oldtown \
     --template-id trade_lp \
     --slug plumber-cm-oldtown-v1 \
     --url https://yourdomain.com/th/plumber/chiang-mai/plumber-cm-oldtown-v1
   ```

3. **Set Up Chat Channel** (via console or API)
4. **Configure Ads Integration** (Meta/Google)
5. **Set Up QR Codes** (if using offline attribution)

## Checklist

- [ ] Client record created with all required fields
- [ ] Onboarding templates initialized
- [ ] UTM policy reviewed and customized
- [ ] Naming policy reviewed and customized
- [ ] Event map reviewed and customized
- [ ] Client configuration verified
- [ ] Onboarding pack generated (optional)

## Troubleshooting

### Client Already Exists
If client ID already exists, the `upsert_client` operation will update it. To start fresh:
1. Delete existing client (via console or direct DB access)
2. Or use a different `client_id`

### Missing Required Fields
All fields marked as required in the Client model must be provided:
- `client_id`, `client_name`, `trade`, `geo_city`, `geo_country`
- `service_area`, `primary_phone`, `lead_email`

### Template Not Found
If you get "template not found" when creating pages:
1. Create template first: `python -m ae.cli create-template ...`
2. Or use existing template: `python -m ae.cli list-templates --db acq.db`

## Example: Complete Client Setup

```bash
# 1. Create client
python -m ae.cli create-client \
  --db acq.db \
  --client-id plumber-cm-oldtown \
  --name "CM Oldtown Plumbing" \
  --trade plumber \
  --city "chiang mai" \
  --phone "+66-80-000-0000" \
  --email "leads@example.com" \
  --service-area "Chiang Mai Old Town"

# 2. Initialize onboarding templates
python -m ae.cli onboarding-init \
  --db acq.db \
  --client-id plumber-cm-oldtown

# 3. Generate onboarding pack
python -m ae.cli generate-onboarding \
  --db acq.db \
  --client-id plumber-cm-oldtown \
  --out-root clients

# 4. Verify
python -m ae.cli get-client \
  --db acq.db \
  --client-id plumber-cm-oldtown
```

## Related Documentation

- [Client Onboarding v1](./CLIENT_ONBOARDING_V1.md)
- [E2E Initialization](./E2E_INITIALIZATION.md)
- [Console Usage](../README.md#console)
