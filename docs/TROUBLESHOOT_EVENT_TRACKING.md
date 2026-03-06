# Troubleshooting Event Tracking Failures

## Common Issues

### Issue 1: Requests Failing with `(failed) net::ERR...`

**Symptoms**:
- Network tab shows red X on requests
- Status: `(failed) net::ERR...`
- Requests to `/v1/event?db=acq.db` fail

**Causes & Fixes**:

#### Cause A: Public API Server Not Running

**Check**:
```powershell
# Try to access health endpoint
curl http://localhost:8001/health
```

**Fix**:
```powershell
# Start public API server
$env:PYTHONPATH="src"
python -m ae.cli run-public --host 127.0.0.1 --port 8001
```

Keep this terminal running!

#### Cause B: Wrong Port

**Check**: Verify the API is running on port 8001:
- Console: `http://localhost:8000` (port 8000)
- Public API: `http://localhost:8001` (port 8001)

**Fix**: Make sure public API is on port 8001, or update `AE_PUBLIC_API_URL` env var

#### Cause C: CORS Error (Already Fixed)

We fixed CORS by switching from `sendBeacon` to `fetch` with explicit CORS mode. If you still see CORS errors:
- Make sure you've republished the page after the fix
- Hard refresh browser (Ctrl+F5)
- Check browser console for CORS error messages

### Issue 2: "Provisional Headers" Warning

**What it means**: Request hasn't completed yet or failed before completion.

**Fix**: 
- Check if API server is running
- Check browser console for error messages
- Verify network connectivity

### Issue 3: Events Not Showing UTM Parameters

**Symptoms**:
- Events are recorded successfully
- But `utm_source`, `utm_medium`, etc. are `null`

**Cause**: No UTM parameters in the URL when page was visited.

**Fix**: 
- Test with UTM parameters in URL:
  ```
  http://localhost:8080/index.html?utm_source=google&utm_medium=cpc&utm_campaign=test
  ```

## Step-by-Step Troubleshooting

### Step 1: Verify Public API is Running

```powershell
# Check if API responds
curl http://localhost:8001/health
```

**Expected**: `{"status":"ok"}` or similar

**If fails**: Start the public API server (see Cause A above)

### Step 2: Verify HTML Has Tracking Code

```powershell
# Check if tracking JavaScript exists
Select-String -Path "exports\static_site\p1\index.html" -Pattern "trackEvent"
```

**Expected**: Should find `trackEvent` function

**If not found**: Republish the page:
```powershell
$env:PYTHONPATH="src"
python -m ae.cli publish-page --db acq.db --page-id p1
```

### Step 3: Check Browser Console

Open browser Developer Tools → Console tab:
- Look for JavaScript errors
- Look for CORS errors
- Look for network errors

### Step 4: Test with Simple URL First

Before testing with UTM parameters, test basic tracking:

1. Open: `http://localhost:8080/index.html` (no UTM params)
2. Click buttons
3. Check if events are recorded (even without UTM)

If this works, then add UTM parameters.

### Step 5: Test with UTM Parameters

Once basic tracking works:

1. Open: `http://localhost:8080/index.html?utm_source=google&utm_medium=cpc&utm_campaign=test`
2. Click buttons
3. Check events show UTM values

## Quick Diagnostic Script

Run this to check everything:

```powershell
$env:PYTHONPATH="src"

Write-Host "Checking Public API..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 2
    Write-Host "  ✅ Public API is running" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Public API is NOT running" -ForegroundColor Red
    Write-Host "  Start it: python -m ae.cli run-public --host 127.0.0.1 --port 8001" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Checking HTML tracking code..." -ForegroundColor Yellow
if (Test-Path "exports\static_site\p1\index.html") {
    $content = Get-Content "exports\static_site\p1\index.html" -Raw
    if ($content -match "trackEvent") {
        Write-Host "  ✅ Tracking JavaScript found" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Tracking JavaScript NOT found" -ForegroundColor Red
        Write-Host "  Republish page: python -m ae.cli publish-page --db acq.db --page-id p1" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ❌ HTML file not found" -ForegroundColor Red
}

Write-Host ""
Write-Host "Checking events..." -ForegroundColor Yellow
$eventScript = @"
from ae import repo
events = repo.list_events('acq.db', 'p1')
print(f'{len(events)}')
"@
$eventCount = python -c $eventScript
Write-Host "  Current events: $eventCount" -ForegroundColor Cyan
```

## Common Error Messages

### `net::ERR_CONNECTION_REFUSED`
**Meaning**: Can't connect to API server
**Fix**: Start public API server on port 8001

### `net::ERR_FAILED`
**Meaning**: Request failed (generic error)
**Fix**: Check API server logs, browser console for details

### `CORS policy` error
**Meaning**: CORS blocking the request
**Fix**: Should be fixed already, but verify:
- Page uses `fetch` with `mode: 'cors'` (not `sendBeacon`)
- API has CORS middleware configured
- Republish page if needed

### `404 Not Found`
**Meaning**: Endpoint doesn't exist
**Fix**: 
- Verify route is registered: `/v1/event`
- Restart console server if you just added the route
- Check API server is running

## Next Steps After Fixing

Once requests succeed:

1. **Test basic tracking** (no UTM)
2. **Test with Google UTM**: `?utm_source=google&utm_medium=cpc&utm_campaign=test`
3. **Test with Meta UTM**: `?utm_source=facebook&utm_medium=cpc&utm_campaign=test`
4. **Check events in console** show UTM values
5. **Verify ad tracking confirmed** message appears
