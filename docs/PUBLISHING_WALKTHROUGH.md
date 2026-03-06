# Publishing Walkthrough: Step-by-Step Guide

This guide walks you through publishing a page from start to finish.

## Prerequisites

- ✅ Client created (`demo1`)
- ✅ Page created (`p1`)
- ✅ Template exists (`trade_lp`)

## Step-by-Step Publishing Process

### Step 1: Record Required Test Events

Before validation, you need to record test events to prove tracking works. The system requires these three events:

```bash
# Set PYTHONPATH (Windows PowerShell)
$env:PYTHONPATH='src'

# Record call_click event
python -m ae.cli record-event `
  --db acq.db `
  --page-id p1 `
  --event-name call_click `
  --params-json '{\"test\":true}'

# Record quote_submit event
python -m ae.cli record-event `
  --db acq.db `
  --page-id p1 `
  --event-name quote_submit `
  --params-json '{\"test\":true}'

# Record thank_you_view event
python -m ae.cli record-event `
  --db acq.db `
  --page-id p1 `
  --event-name thank_you_view `
  --params-json '{\"test\":true}'
```

**Note**: In PowerShell, use backticks (`) for line continuation and escape quotes with `\"`.

**Alternative (single line)**:
```powershell
python -m ae.cli record-event --db acq.db --page-id p1 --event-name call_click --params-json '{\"test\":true}'
python -m ae.cli record-event --db acq.db --page-id p1 --event-name quote_submit --params-json '{\"test\":true}'
python -m ae.cli record-event --db acq.db --page-id p1 --event-name thank_you_view --params-json '{\"test\":true}'
```

### Step 2: Verify Events Were Recorded

```bash
python -c "from ae import repo; events = repo.list_events('acq.db', page_id='p1'); print(f'Events: {len(events)}'); [print(f'  - {e.event_name}') for e in events]"
```

You should see all three events listed.

### Step 3: Validate the Page

```bash
python -m ae.cli validate-page --db acq.db --page-id p1
```

**Expected output**:
- ✅ `OK: publish readiness passed` - Success!
- ❌ `FAIL: publish readiness failed` - Check errors listed

**Common validation errors**:
- `Tracking not validated: expected events not confirmed firing`
  - **Fix**: Make sure all 3 events are recorded (Step 1)
- `Missing client.primary_phone` or `Missing client.lead_email`
  - **Fix**: Update client record with required fields

### Step 4: Publish the Page

Once validation passes:

```bash
python -m ae.cli publish-page --db acq.db --page-id p1
```

**What happens**:
1. Validates the page (must pass)
2. Builds content using `StubContentAdapter`:
   - Generates headline: `"Plumber in Brisbane — Fast, Clean, Verified"`
   - Generates subheadline, CTAs, sections
3. Publishes using `TailwindStaticSitePublisher`:
   - Creates HTML file at `exports/static_site/p1/index.html`
   - Includes CSS assets
4. Updates page status to `live`
5. Creates publish log entry

**Expected output**:
- ✅ `OK: page published (live)` - Success!

### Step 5: Locate Published File

The published HTML is at:
```
exports/static_site/p1/index.html
```

**Check if it exists**:
```powershell
Test-Path "exports\static_site\p1\index.html"
```

**View file location**:
```powershell
Get-Item "exports\static_site\p1\index.html" | Select-Object FullName
```

### Step 6: Preview the Published Page

**Option A: Open directly**
- Double-click `exports/static_site/p1/index.html` in File Explorer
- Or right-click → Open with → Browser

**Option B: Serve with Python**
```bash
cd exports/static_site/p1
python -m http.server 8080
```
Then open: `http://localhost:8080/index.html`

**Option C: Serve entire exports directory**
```bash
cd exports/static_site
python -m http.server 8080
```
Then open: `http://localhost:8080/p1/index.html`

## Complete Command Sequence

Here's the complete sequence in one block:

```powershell
# Set environment
$env:PYTHONPATH='src'

# Step 1: Record events
python -m ae.cli record-event --db acq.db --page-id p1 --event-name call_click --params-json '{\"test\":true}'
python -m ae.cli record-event --db acq.db --page-id p1 --event-name quote_submit --params-json '{\"test\":true}'
python -m ae.cli record-event --db acq.db --page-id p1 --event-name thank_you_view --params-json '{\"test\":true}'

# Step 2: Validate
python -m ae.cli validate-page --db acq.db --page-id p1

# Step 3: Publish
python -m ae.cli publish-page --db acq.db --page-id p1

# Step 4: Check output
Test-Path "exports\static_site\p1\index.html"
```

## Troubleshooting

### "unable to open database file"
**Issue**: Database path not found

**Solution**: Use absolute path or ensure you're in the project root:
```bash
cd d:\aqusition_os
python -m ae.cli validate-page --db acq.db --page-id p1
```

### "JSONDecodeError: Expecting property name"
**Issue**: JSON quotes not escaped properly in PowerShell

**Solution**: Use escaped quotes `\"` or single quotes around JSON:
```powershell
--params-json '{\"test\":true}'
```

### "Tracking not validated"
**Issue**: Events not recorded or wrong event names

**Solution**: 
1. Check event names match exactly: `call_click`, `quote_submit`, `thank_you_view`
2. Verify events exist: `python -c "from ae import repo; print([e.event_name for e in repo.list_events('acq.db', 'p1')])"`

### "Missing client.primary_phone"
**Issue**: Client record incomplete

**Solution**: Update client:
```bash
python -c "from ae import repo; from ae.models import Client; c = repo.get_client('acq.db', 'demo1'); c.primary_phone = '+61-400-000-000'; repo.upsert_client('acq.db', c)"
```

### Published file not found
**Issue**: Publish succeeded but file missing

**Solution**: Check default output directory:
- Default: `exports/static_site/{page_id}/index.html`
- Can be overridden with `--static-out-dir` flag

## What Gets Generated

When you publish, the system generates:

1. **HTML file**: `exports/static_site/p1/index.html`
   - Complete landing page HTML
   - Includes embedded CSS (from `src/ae/assets/tailwind_compiled.css`)
   - Responsive design
   - Ready to deploy

2. **Assets directory**: `exports/static_site/p1/assets/`
   - CSS file: `assets/styles.css`
   - Other assets as needed

3. **Content structure**:
   - Hero section with headline/subheadline
   - Call-to-action buttons
   - Benefits section
   - Proof section
   - FAQ section

## Next Steps After Publishing

1. **Review the HTML**: Open and check the generated page
2. **Customize content**: Edit the HTML or modify content adapter
3. **Deploy**: Upload to your hosting/CDN
4. **Test**: Visit the live URL and test functionality
5. **Monitor**: Check events are firing correctly

## Using Console UI

You can also publish via the console UI:

1. Go to `http://localhost:8000/console`
2. Click "📄 Load pages"
3. Find your page card
4. Click "✓ Validate" button
5. If validation passes, click "🚀 Publish" button

The console will show success/error messages via toast notifications.

## Summary

**Publishing requires**:
1. ✅ Page record exists
2. ✅ Client exists with required fields
3. ✅ Template exists
4. ✅ Test events recorded (`call_click`, `quote_submit`, `thank_you_view`)
5. ✅ Validation passes
6. ✅ Publish command succeeds

**Result**:
- HTML file generated at `exports/static_site/{page_id}/index.html`
- Page status changed to `live`
- Ready to deploy and serve traffic
