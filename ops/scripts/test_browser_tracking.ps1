# PowerShell script to test browser tracking
# Usage: .\ops\scripts\test_browser_tracking.ps1 [page_id] [db_path]

param(
    [string]$PageId = "p1",
    [string]$DbPath = "acq.db"
)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Browser Tracking Test" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if API is running
Write-Host "[1/4] Checking if Public API is running..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 2 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "  ✅ Public API is running" -ForegroundColor Green
    }
} catch {
    Write-Host "  ❌ Public API is NOT running" -ForegroundColor Red
    Write-Host "  Start it with: python -m ae.cli run-public --host 127.0.0.1 --port 8001" -ForegroundColor Yellow
    Write-Host "  Or run: .\ops\scripts\start_public_api.ps1" -ForegroundColor Yellow
    exit 1
}

# Step 2: Get baseline event count
Write-Host ""
Write-Host "[2/4] Getting baseline event count..." -ForegroundColor Yellow
$env:PYTHONPATH = "src"
$beforeScript = @"
from ae import repo
events = repo.list_events('$DbPath', '$PageId')
browser_events = [e for e in events if 'url' in e.params_json]
print(f'{len(events)}')
print(f'{len(browser_events)}')
"@

$beforeResult = python -c $beforeScript
$beforeTotal, $beforeBrowser = $beforeResult -split "`n" | Where-Object { $_ -ne "" }
Write-Host "  Total events before: $beforeTotal" -ForegroundColor Cyan
Write-Host "  Browser events before: $beforeBrowser" -ForegroundColor Cyan

# Step 3: Start HTTP server for HTML
Write-Host ""
Write-Host "[3/4] Starting HTTP server for HTML page..." -ForegroundColor Yellow
$htmlPath = "exports\static_site\$PageId\index.html"
if (-not (Test-Path $htmlPath)) {
    Write-Host "  ❌ HTML file not found: $htmlPath" -ForegroundColor Red
    Write-Host "  Publish the page first: python -m ae.cli publish-page --db $DbPath --page-id $PageId" -ForegroundColor Yellow
    exit 1
}

Write-Host "  ✅ HTML file found: $htmlPath" -ForegroundColor Green
Write-Host ""
Write-Host "  Starting HTTP server on port 8080..." -ForegroundColor Cyan
Write-Host "  Open in browser: http://localhost:8080/index.html" -ForegroundColor Green
Write-Host ""
Write-Host "  Instructions:" -ForegroundColor Yellow
Write-Host "    1. Open http://localhost:8080/index.html in your browser" -ForegroundColor White
Write-Host "    2. Open browser Developer Tools (F12)" -ForegroundColor White
Write-Host "    3. Go to Network tab" -ForegroundColor White
Write-Host "    4. Click 'Book now' button → should trigger call_click event" -ForegroundColor White
Write-Host "    5. Click 'Get a quote' button → should trigger quote_submit event" -ForegroundColor White
Write-Host "    6. Check Network tab for POST requests to /v1/event" -ForegroundColor White
Write-Host ""
Write-Host "  Press Ctrl+C to stop the HTTP server and check results" -ForegroundColor Yellow
Write-Host ""

# Start HTTP server in background
$serverJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    cd "exports\static_site\$using:PageId"
    python -m http.server 8080
}

# Wait for user to test
Write-Host "  HTTP server started. Test in browser, then press Enter to continue..." -ForegroundColor Cyan
Read-Host

# Stop HTTP server
Stop-Job $serverJob
Remove-Job $serverJob

# Step 4: Check for new events
Write-Host ""
Write-Host "[4/4] Checking for new browser events..." -ForegroundColor Yellow
$afterScript = @"
from ae import repo
import json

events = repo.list_events('$DbPath', '$PageId')
browser_events = [e for e in events if 'url' in e.params_json]

print(f'{len(events)}')
print(f'{len(browser_events)}')

if browser_events:
    print('Recent browser events:')
    for e in sorted(browser_events, key=lambda x: x.timestamp, reverse=True)[:5]:
        print(f'  - {e.event_name.value} at {e.timestamp}')
        if 'url' in e.params_json:
            print(f'    URL: {e.params_json[\"url\"]}')
"@

$afterResult = python -c $afterScript
Write-Host ""
Write-Host $afterResult

# Summary
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$afterTotal, $afterBrowser = ($afterResult -split "`n" | Where-Object { $_ -match "^\d+$" })
$newEvents = [int]$afterTotal - [int]$beforeTotal
$newBrowserEvents = [int]$afterBrowser - [int]$beforeBrowser

if ($newBrowserEvents -gt 0) {
    Write-Host "✅ SUCCESS! Browser tracking is working!" -ForegroundColor Green
    Write-Host "   New browser events recorded: $newBrowserEvents" -ForegroundColor Green
} else {
    Write-Host "⚠️  No new browser events detected" -ForegroundColor Yellow
    Write-Host "   Check:" -ForegroundColor Yellow
    Write-Host "   - Browser console for JavaScript errors" -ForegroundColor White
    Write-Host "   - Network tab for failed API requests" -ForegroundColor White
    Write-Host "   - CORS configuration (AE_PUBLIC_CORS_ORIGINS)" -ForegroundColor White
}
