# Quick test script - assumes API is already running
# Usage: .\ops\scripts\quick_test_tracking.ps1 [page_id] [db_path]

param(
    [string]$PageId = "p1",
    [string]$DbPath = "acq.db"
)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Quick Browser Tracking Test" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Set PYTHONPATH
$env:PYTHONPATH = "src"

# Get baseline
Write-Host "[1/3] Getting baseline event count..." -ForegroundColor Yellow
$beforeScript = @"
from ae import repo
events = repo.list_events('$DbPath', '$PageId')
browser_events = [e for e in events if 'url' in e.params_json or 'referrer' in e.params_json]
print(f'{len(events)}')
print(f'{len(browser_events)}')
"@

$beforeResult = python -c $beforeScript
$beforeTotal, $beforeBrowser = $beforeResult -split "`n" | Where-Object { $_ -ne "" }
Write-Host "  Total events: $beforeTotal" -ForegroundColor Cyan
Write-Host "  Browser events: $beforeBrowser" -ForegroundColor Cyan

# Check HTML exists
Write-Host ""
Write-Host "[2/3] Checking HTML file..." -ForegroundColor Yellow
$htmlPath = "exports\static_site\$PageId\index.html"
if (-not (Test-Path $htmlPath)) {
    Write-Host "  ❌ HTML file not found: $htmlPath" -ForegroundColor Red
    exit 1
}
Write-Host "  ✅ HTML file found" -ForegroundColor Green

# Instructions
Write-Host ""
Write-Host "[3/3] Testing instructions:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Step 1: Start HTTP server (in a NEW terminal):" -ForegroundColor Cyan
Write-Host "    cd exports\static_site\$PageId" -ForegroundColor White
Write-Host "    python -m http.server 8080" -ForegroundColor White
Write-Host ""
Write-Host "  Step 2: Open browser:" -ForegroundColor Cyan
Write-Host "    http://localhost:8080/index.html" -ForegroundColor Green
Write-Host ""
Write-Host "  Step 3: Open Developer Tools (F12):" -ForegroundColor Cyan
Write-Host "    - Go to Network tab" -ForegroundColor White
Write-Host "    - Filter: XHR or Fetch" -ForegroundColor White
Write-Host ""
Write-Host "  Step 4: Click buttons:" -ForegroundColor Cyan
Write-Host "    - Click 'Book now' → should see POST to /v1/event" -ForegroundColor White
Write-Host "    - Click 'Get a quote' → should see POST to /v1/event" -ForegroundColor White
Write-Host ""
Write-Host "  Step 5: Run this command again to check results:" -ForegroundColor Cyan
Write-Host "    .\ops\scripts\quick_test_tracking.ps1" -ForegroundColor White
Write-Host ""

# Check API
Write-Host "Checking API status..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "  ✅ Public API is running" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  Public API check failed (may still work)" -ForegroundColor Yellow
    Write-Host "  Make sure API is running: python -m ae.cli run-public" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Press Enter after you've clicked the buttons..." -ForegroundColor Cyan
Read-Host

# Check results
Write-Host ""
Write-Host "Checking for new events..." -ForegroundColor Yellow
$afterScript = @"
from ae import repo
import json

events = repo.list_events('$DbPath', '$PageId')
browser_events = [e for e in events if 'url' in e.params_json or 'referrer' in e.params_json]

print(f'Total events: {len(events)}')
print(f'Browser events: {len(browser_events)}')

if browser_events:
    print('')
    print('Recent browser events:')
    for e in sorted(browser_events, key=lambda x: x.timestamp, reverse=True)[:5]:
        print(f'  ✅ {e.event_name.value}')
        print(f'     Time: {e.timestamp}')
        if 'url' in e.params_json:
            print(f'     URL: {e.params_json[\"url\"][:60]}...')
"@

$afterResult = python -c $afterScript
Write-Host $afterResult

# Summary
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$afterLines = $afterResult -split "`n" | Where-Object { $_ -match "^\d+$" -or $_ -match "Browser events:" }
$afterTotal = ($afterLines | Where-Object { $_ -match "^Total events:" }) -replace "Total events: ", ""
$afterBrowser = ($afterLines | Where-Object { $_ -match "^Browser events:" }) -replace "Browser events: ", ""

if ([int]$afterBrowser -gt [int]$beforeBrowser) {
    Write-Host "✅ SUCCESS! Browser tracking is working!" -ForegroundColor Green
    Write-Host "   New browser events: $([int]$afterBrowser - [int]$beforeBrowser)" -ForegroundColor Green
} elseif ([int]$afterBrowser -eq [int]$beforeBrowser -and [int]$afterBrowser -gt 0) {
    Write-Host "✅ Browser events exist, but no new ones detected" -ForegroundColor Yellow
    Write-Host "   Try clicking buttons again" -ForegroundColor Yellow
} else {
    Write-Host "⚠️  No browser events detected" -ForegroundColor Yellow
    Write-Host "   Troubleshooting:" -ForegroundColor Yellow
    Write-Host "   - Check browser console for errors" -ForegroundColor White
    Write-Host "   - Check Network tab for failed requests" -ForegroundColor White
    Write-Host "   - Verify API is running: curl http://localhost:8001/health" -ForegroundColor White
}
