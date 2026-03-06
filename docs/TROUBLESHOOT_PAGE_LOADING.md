# Troubleshooting Page Loading Issues

## Issue: Pages Not Loading

If pages are not loading in the console, follow these steps:

## Quick Checks

### 1. Check Browser Console
Open browser DevTools (F12) and check the Console tab for errors:
- Look for `[Router]` prefixed messages
- Check for JavaScript errors
- Verify scripts are loading

### 2. Check Network Tab
- Verify `/console_static/pages/service-packages.html` returns 200 OK
- Check if `/console_static/shared/router.js` loads successfully
- Look for any 404 or 500 errors

### 3. Verify Router Initialization
In browser console, type:
```javascript
window.router
```
Should return the Router instance. If `undefined`, router didn't initialize.

### 4. Check Current Route
```javascript
window.router.getCurrentPath()
```
Should return the current route path.

### 5. Check Registered Routes
```javascript
Array.from(window.router.routes.keys())
```
Should show all registered routes.

## Common Issues & Fixes

### Issue: Router Not Initialized
**Symptoms**: `window.router` is undefined

**Fix**: 
1. Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
2. Check that `router.js` is accessible at `/console_static/shared/router.js`
3. Check browser console for script loading errors

### Issue: Page Container Not Found
**Symptoms**: Console shows `[Router] Page container not found`

**Fix**:
1. Verify `index.html` has `<div id="page-container">` element
2. Check that router.js loads after index.html DOM is ready

### Issue: Scripts Not Executing
**Symptoms**: Page HTML loads but functions don't work

**Fix**:
1. Check browser console for script execution errors
2. Verify scripts are appended to `<body>` (check Elements tab)
3. Functions should be available on `window` object

### Issue: Auto-Load Functions Not Running
**Symptoms**: Page loads but data doesn't appear

**Fix**:
1. Check console for auto-load messages
2. Manually call the load function: `loadServicePackages()`
3. Verify API endpoints are accessible

## Manual Testing

### Test Router Navigation
```javascript
// Navigate to service packages
window.router.navigate('/service-packages');

// Check if page loaded
document.getElementById('packages-list')
```

### Test Page Loading Directly
```javascript
// Load page HTML directly
await window.router.loadPage('service-packages.html');

// Check if content appeared
document.getElementById('page-container').innerHTML.length
```

### Test API Endpoints
```javascript
// Test API call
const db = 'acq.db';
const response = await api(`/api/service-packages?db=${db}`);
console.log(response);
```

## Debug Mode

Enable verbose logging by adding to browser console:
```javascript
// Enable router debug logging
window.router._debug = true;
```

## Recent Fixes Applied

1. **Router Script Cleanup**: Removed premature script removal that was breaking functions
2. **Auto-Load Timing**: Improved auto-load function to wait for DOM and retry with limits
3. **Error Handling**: Added better error messages and retry logic

## Still Not Working?

1. Check server logs for errors
2. Verify database path is correct (`acq.db` or custom)
3. Check authentication (if required)
4. Verify all static files are accessible
5. Try clearing browser cache

## Expected Behavior

When navigating to `/console#/service-packages`:

1. Router detects hash change
2. Router fetches `service-packages.html`
3. HTML is inserted into `page-container`
4. Scripts are extracted and executed
5. Auto-load function runs after DOM is ready
6. `loadServicePackages()` is called
7. API request is made
8. Packages are displayed

Check browser console for `[Router]` and `[service-packages]` messages to trace the flow.
