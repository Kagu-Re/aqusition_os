# Post-Onboarding: Next Steps

After completing client onboarding, follow these steps to get the landing page published and ready for traffic.

## Overview

The next step in the pilot checklist is **"Landing published"**. This involves:
1. Ensuring a template exists
2. Creating the landing page
3. Configuring page content
4. Validating the page
5. Publishing the page
6. Setting up tracking and attribution

## Step 1: Review Onboarding Templates (If Not Done)

Before creating pages, ensure your onboarding templates are customized:

```bash
# Check templates exist
python -m ae.cli onboarding-init --db acq.db --client-id YOUR_CLIENT_ID

# Review via console
# Open: http://localhost:8000/console/onboarding?client_id=YOUR_CLIENT_ID
```

**Key Points to Verify**:
- ✅ UTM policy matches your ad platform setup
- ✅ Naming policy defines your page ID format
- ✅ Event map matches your tracking implementation

## Step 2: Ensure Template Exists

A template defines the structure and schema for landing pages. Check if you have a suitable template:

```bash
# List existing templates (via SQL query)
python -c "import sqlite3; conn = sqlite3.connect('acq.db'); cur = conn.execute('SELECT template_id, template_version, status FROM templates'); [print(f'{r[0]} v{r[1]} ({r[2]})') for r in cur.fetchall()]; conn.close()"
```

**If no template exists**, create one:

```bash
python -m ae.cli create-template \
  --db acq.db \
  --template-id trade_lp \
  --version 1.0.0 \
  --cms-schema 1.0 \
  --events 1.0
```

**Common Templates**:
- `trade_lp` - Generic trade landing page template
- Custom templates for specific industries/use cases

## Step 3: Create Landing Page

Create a landing page using your client ID and template:

```bash
python -m ae.cli create-page \
  --db acq.db \
  --page-id p-YOUR_CLIENT_ID-v1 \
  --client-id YOUR_CLIENT_ID \
  --template-id trade_lp \
  --slug your-client-slug-v1 \
  --url https://yourdomain.com/path/to/page
```

**Page ID Format** (follow naming policy):
- Use prefix: `p-` (as per naming policy)
- Include client ID: `p-plumber-cm-oldtown-v1`
- Include version: `-v1`, `-v2` for iterations

**URL Format**:
- Should match your domain structure
- Example: `https://yourdomain.com/th/plumber/chiang-mai/plumber-cm-oldtown-v1`
- Include geo path if relevant

**Example**:
```bash
python -m ae.cli create-page \
  --db acq.db \
  --page-id p-plumber-cm-oldtown-v1 \
  --client-id plumber-cm-oldtown \
  --template-id trade_lp \
  --slug plumber-cm-oldtown-v1 \
  --url https://yourdomain.com/th/plumber/chiang-mai/plumber-cm-oldtown-v1
```

## Step 4: Configure Page Content

After creating the page, configure its content. This can be done via:

### Option A: Console UI (Recommended)
1. Start console: `python -m ae.cli serve-console`
2. Navigate to: `http://localhost:8000/console/pages`
3. Find your page and edit content
4. Configure:
   - Hero section (headline, description)
   - Service focus
   - Call-to-action buttons
   - Contact information
   - Pricing/offer details

### Option B: Python API
```python
from ae import repo
from ae.models import Page

page = repo.get_page('acq.db', 'p-plumber-cm-oldtown-v1')
# Update page content via API or direct DB access
```

### Option C: Content Management System
If your template uses a CMS integration, configure content through that system.

## Step 5: Validate Page

Before publishing, validate the page:

```bash
python -m ae.cli validate-page \
  --db acq.db \
  --page-id p-YOUR_CLIENT_ID-v1
```

**Validation Checks**:
- ✅ Required fields populated
- ✅ Content structure valid
- ✅ Tracking code installed
- ✅ UTM parameters configured
- ✅ Event tracking implemented
- ✅ Links and CTAs functional

**Fix Any Errors**:
- Review validation output
- Update page content
- Re-validate until all checks pass

## Step 6: Publish Page

Once validated, publish the page:

```bash
python -m ae.cli publish-page \
  --db acq.db \
  --page-id p-YOUR_CLIENT_ID-v1
```

**What Happens**:
1. Page status changes to `live`
2. Content is published to hosting/CDN
3. Tracking code is activated
4. Page becomes accessible at the configured URL

**Verify Publication**:
- Visit the published URL
- Check that content renders correctly
- Verify tracking code fires (check browser console)
- Test form submissions and CTAs

## Step 7: Set Up Tracking & Attribution

### Install Tracking Code

Based on your event map, ensure tracking is implemented:

**Required Events** (from event map):
- `page_view` - Fires on page load
- `view_content` - Fires on engagement (scroll, pricing view)
- `generate_lead` - Fires on form submit/WhatsApp click
- `booking` - Fires on booking confirmation

**Implementation**:
- Add GA4 tracking code (if using Google Analytics)
- Add Meta Pixel (if using Meta ads)
- Implement event tracking JavaScript
- Test events fire correctly

### Configure UTM Parameters

Based on your UTM policy, ensure ads use correct parameters:

**Example** (from UTM policy):
```
?utm_source=google&utm_medium=paid&utm_campaign=plumber-cm-oldtown-feb&utm_content=headline-a&utm_term=plumber-near-me
```

**Verify**:
- Ads platform uses correct UTM structure
- Landing page preserves UTM parameters
- Analytics captures UTM data correctly

## Step 8: Test Attribution

Before launching ads, test attribution:

```bash
# Record a test event
python -m ae.cli record-event \
  --db acq.db \
  --page-id p-YOUR_CLIENT_ID-v1 \
  --event-name page_view \
  --params-json '{"utm_source":"test","utm_medium":"manual","utm_campaign":"qa-test"}'

# Check event was recorded
python -c "from ae import repo; events = repo.list_events('acq.db', page_id='p-YOUR_CLIENT_ID-v1'); print(f'Found {len(events)} events')"
```

**Manual Test**:
1. Visit page with UTM parameters
2. Submit form or click CTA
3. Check that events are recorded
4. Verify UTM data is captured correctly

## Step 9: Set Up Chat Channel (Optional)

If using chat automation:

```python
from ae import repo
from ae.enums import ChatProvider

repo.upsert_chat_channel(
    db_path="acq.db",
    channel_id="ch_YOUR_CLIENT_ID_whatsapp",
    provider=ChatProvider.whatsapp,
    handle="+66-80-000-0000",  # Client's phone
    display_name="Your Client WhatsApp",
    meta_json={"client_id": "YOUR_CLIENT_ID"},
)
```

Or via console API:
```bash
curl -X POST http://localhost:8000/api/chat-channels?db=acq.db \
  -H "Content-Type: application/json" \
  -H "X-AE-SECRET: YOUR_SECRET" \
  -d '{
    "channel_id": "ch_YOUR_CLIENT_ID_whatsapp",
    "provider": "whatsapp",
    "handle": "+66-80-000-0000",
    "display_name": "Your Client WhatsApp",
    "meta": {"client_id": "YOUR_CLIENT_ID"}
  }'
```

## Step 10: Generate QR Code (If Using Offline Attribution)

If using QR codes for offline attribution:

```bash
curl -X POST "http://localhost:8000/api/qr/generate?db=acq.db" \
  -H "Content-Type: application/json" \
  -H "X-AE-SECRET: YOUR_SECRET" \
  -d '{
    "attribution_id": "aid_YOUR_CLIENT_ID_menu",
    "client_id": "YOUR_CLIENT_ID",
    "url": "https://yourdomain.com/menu-YOUR_CLIENT_ID.html",
    "enable_attribution": true
  }'
```

## Complete Workflow Example

Here's a complete example for client `plumber-cm-oldtown`:

```bash
# 1. Verify onboarding templates
python -m ae.cli onboarding-init --db acq.db --client-id plumber-cm-oldtown

# 2. Check/create template
python -m ae.cli create-template \
  --db acq.db \
  --template-id trade_lp \
  --version 1.0.0 \
  --cms-schema 1.0 \
  --events 1.0

# 3. Create page
python -m ae.cli create-page \
  --db acq.db \
  --page-id p-plumber-cm-oldtown-v1 \
  --client-id plumber-cm-oldtown \
  --template-id trade_lp \
  --slug plumber-cm-oldtown-v1 \
  --url https://yourdomain.com/th/plumber/chiang-mai/plumber-cm-oldtown-v1

# 4. Configure content (via console UI)
# Open: http://localhost:8000/console/pages

# 5. Validate
python -m ae.cli validate-page --db acq.db --page-id p-plumber-cm-oldtown-v1

# 6. Publish
python -m ae.cli publish-page --db acq.db --page-id p-plumber-cm-oldtown-v1

# 7. Test attribution
python -m ae.cli record-event \
  --db acq.db \
  --page-id p-plumber-cm-oldtown-v1 \
  --event-name page_view \
  --params-json '{"utm_source":"test","utm_campaign":"qa"}'

# 8. Verify page is live
# Visit: https://yourdomain.com/th/plumber/chiang-mai/plumber-cm-oldtown-v1
```

## Checklist: Landing Published

- [ ] Onboarding templates reviewed/customized
- [ ] Template exists (or created)
- [ ] Landing page created
- [ ] Page content configured
- [ ] Page validated (no errors)
- [ ] Page published (status = live)
- [ ] Page accessible at URL
- [ ] Tracking code installed
- [ ] Events fire correctly
- [ ] UTM parameters configured
- [ ] Attribution tested
- [ ] Chat channel set up (if using)
- [ ] QR code generated (if using)

## Next Steps in Pilot Checklist

After "Landing published", continue with:

1. **Ads/QR tested** - Test ad campaigns and QR codes
2. **Attribution verified** - Verify UTM tracking works
3. **Lead validated** - Test lead intake and routing
4. **Chat linked** - Connect chat automation
5. **Booking tested** - Test booking workflow
6. **Payment tested** - Test payment processing
7. **Reconciliation tested** - Verify data reconciliation
8. **SLA running** - Set up service level agreements
9. **Export scheduled** - Schedule data exports
10. **Backup enabled** - Enable database backups

## Troubleshooting

### Page Creation Fails
- **Error**: "Template not found"
  - **Solution**: Create template first or use existing template ID

- **Error**: "Client not found"
  - **Solution**: Verify client exists: `python -c "from ae import repo; print(repo.get_client('acq.db', 'YOUR_CLIENT_ID'))"`

### Validation Fails
- **Error**: "Missing required fields"
  - **Solution**: Configure page content via console UI

- **Error**: "Tracking code not found"
  - **Solution**: Install tracking code before publishing

### Publication Fails
- **Error**: "Publish adapter error"
  - **Solution**: Check adapter configuration, verify hosting/CDN access

- **Error**: "URL already in use"
  - **Solution**: Use different page ID or URL

## Related Documentation

- [Pilot Checklist](../README_v1_1_Pilot.md)
- [Client Configuration](./PILOT_CLIENT_CONFIGURATION.md)
- [How Onboarding Works](./HOW_ONBOARDING_WORKS.md)
- [CLI Operations](./CLI_OPERATIONS.md)
- [E2E Initialization](./E2E_INITIALIZATION.md)
