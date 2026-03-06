# Service Package Flow - Definition of Ready (DOR) & Definition of Done (DOD)

## Definition of Ready (DOR) - Pre-Test Checklist

Before testing the full package selection flow, ensure:

### ✅ Database & Data
- [ ] Database file exists: `acq.db`
- [ ] Test client exists: `test-massage-spa` with `business_model=fixed_price`
- [ ] Service packages exist (at least 3 packages for `test-massage-spa`)
- [ ] Landing page exists: `demo-service-page` using `service_lp` template
- [ ] Landing page is published (status: `live`)
- [ ] Chat channel exists: Telegram channel for `test-massage-spa`

### ✅ Code & Configuration
- [ ] `package_selected` event added to `EventName` enum
- [ ] Public API code updated (accepts `package_selected` events)
- [ ] Service template (`service_lp`) exists and is active
- [ ] Content adapter supports service template
- [ ] Publisher adapter supports service template sections

### ✅ Services Running
- [ ] Public API server running on port 8001
- [ ] Database accessible (no locks/errors)
- [ ] CORS configured correctly (if testing from browser)

### ✅ Test Environment
- [ ] Landing page HTML file exists: `exports/static_site/demo-service-page/index.html`
- [ ] Landing page can be served (via file:// or http server)
- [ ] Browser console accessible (for debugging)
- [ ] Network tab accessible (to verify API calls)

## Definition of Done (DOD) - Success Criteria

After clicking a package, verify:

### ✅ Event Tracking
- [ ] `package_selected` event is tracked
- [ ] Event stored in database with correct `page_id`
- [ ] Event params include:
  - `package_id`
  - `package_name`
  - `package_price`
  - `timestamp`
  - `url`
  - `referrer` (if applicable)
  - UTM parameters (if present in URL)

### ✅ Lead Creation
- [ ] Lead is created in database
- [ ] Lead has correct `client_id`: `test-massage-spa`
- [ ] Lead has correct `page_id`: `demo-service-page`
- [ ] Lead `message` contains: "Package selected: {package_name}"
- [ ] Lead `meta_json` contains:
  - `package_id`
  - `package_name`
  - `package_price`

### ✅ Chat Redirect
- [ ] User is redirected to Telegram URL
- [ ] Telegram URL format: `https://t.me/{username}?package={package_id}`
- [ ] Package ID is correctly appended as query parameter
- [ ] Redirect happens after event/lead are sent (200ms delay)

### ✅ Error Handling
- [ ] No JavaScript errors in browser console
- [ ] No API errors (4xx/5xx responses)
- [ ] Failed API calls don't break page functionality
- [ ] Graceful fallback if chat channel not configured

### ✅ Data Verification
- [ ] Can query events: `repo.list_events('acq.db')` shows `package_selected`
- [ ] Can query leads: `repo.list_leads('acq.db')` shows lead with package metadata
- [ ] Event and lead timestamps are reasonable (within last few minutes)
- [ ] No duplicate events/leads from same click

## Test Flow Steps

1. **Start Services**
   ```powershell
   .\start_service_package_test.bat
   ```

2. **Open Landing Page**
   - Navigate to: `exports/static_site/demo-service-page/index.html`
   - Or serve via: `python -m http.server 8080` in that directory

3. **Verify Page Load**
   - Page loads without errors
   - Service packages section appears
   - Packages are displayed (3 cards visible)
   - "Select Package" buttons are clickable

4. **Click Package**
   - Click any "Select Package" button
   - Observe browser behavior

5. **Verify Results**
   ```powershell
   python check_package_events.py
   ```

6. **Check Database**
   ```python
   from ae import repo
   events = repo.list_events('acq.db')
   leads = repo.list_leads('acq.db')
   ```

## Troubleshooting

### Packages Not Loading
- Check: Public API running on port 8001?
- Check: Browser console for fetch errors?
- Check: CORS headers configured?

### Event Not Tracked
- Check: `package_selected` in EventName enum?
- Check: API server restarted after code changes?
- Check: Browser console for API errors?

### No Redirect
- Check: Chat channel configured?
- Check: `chatUrl` variable set in JavaScript?
- Check: Browser console for errors?

### Lead Not Created
- Check: API endpoint `/lead` accessible?
- Check: Database write permissions?
- Check: API response for errors?
