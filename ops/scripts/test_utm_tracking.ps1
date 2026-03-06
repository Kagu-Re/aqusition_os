# PowerShell script to test UTM parameter tracking
# Usage: .\ops\scripts\test_utm_tracking.ps1 [page_id] [db_path]

param(
    [string]$PageId = "p1",
    [string]$DbPath = "acq.db"
)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "UTM Parameter Tracking Test" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Set PYTHONPATH
$env:PYTHONPATH = "src"

# Get baseline
Write-Host "[1/4] Getting baseline event count..." -ForegroundColor Yellow
$beforeScript = @"
from ae import repo
events = repo.list_events('$DbPath', '$PageId')
print(f'{len(events)}')
"@

$beforeCount = python -c $beforeScript
Write-Host "  Current events: $beforeCount" -ForegroundColor Cyan

# Instructions
Write-Host ""
Write-Host "[2/4] Testing instructions:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Step 1: Start HTTP server (in a NEW terminal):" -ForegroundColor Cyan
Write-Host "    cd exports\static_site\$PageId" -ForegroundColor White
Write-Host "    python -m http.server 8080" -ForegroundColor White
Write-Host ""
Write-Host "  Step 2: Test Google Ads tracking:" -ForegroundColor Cyan
Write-Host "    Open in browser:" -ForegroundColor White
$googleUrl = "http://localhost:8080/index.html?utm_source=google&utm_medium=cpc&utm_campaign=test-google&utm_content=ad-a&utm_term=test-keyword"
Write-Host "    $googleUrl" -ForegroundColor Green
Write-Host ""
Write-Host "    Click 'Book now' button" -ForegroundColor White
Write-Host ""
Write-Host "  Step 3: Test Meta Ads tracking:" -ForegroundColor Cyan
Write-Host "    Open in browser:" -ForegroundColor White
$metaUrl = "http://localhost:8080/index.html?utm_source=facebook&utm_medium=cpc&utm_campaign=test-meta&utm_content=creative-1"
Write-Host "    $metaUrl" -ForegroundColor Green
Write-Host ""
Write-Host "    Click 'Get a quote' button" -ForegroundColor White
Write-Host ""
Write-Host "  Step 4: Press Enter after testing..." -ForegroundColor Cyan
Read-Host

# Check results
Write-Host ""
Write-Host "[3/4] Checking for events with UTM parameters..." -ForegroundColor Yellow
$checkScript = @"
from ae import repo
import json

events = repo.list_events('$DbPath', '$PageId')
google_events = []
meta_events = []
no_utm_events = []

for e in events:
    params = e.params_json
    utm_source = params.get('utm_source') if isinstance(params, dict) else None
    
    if utm_source == 'google':
        google_events.append(e)
    elif utm_source in ['facebook', 'meta', 'instagram']:
        meta_events.append(e)
    elif utm_source is None:
        no_utm_events.append(e)

print(f'Total events: {len(events)}')
print(f'Google events: {len(google_events)}')
print(f'Meta events: {len(meta_events)}')
print(f'No UTM events: {len(no_utm_events)}')
print('')

if google_events:
    print('Google Ads events:')
    for e in sorted(google_events, key=lambda x: x.timestamp, reverse=True)[:3]:
        params = e.params_json
        print(f'  [OK] {e.event_name.value}')
        print(f'     Campaign: {params.get(\"utm_campaign\", \"N/A\")}')
        print(f'     Content: {params.get(\"utm_content\", \"N/A\")}')
        print(f'     Term: {params.get(\"utm_term\", \"N/A\")}')
        print('')

if meta_events:
    print('Meta Ads events:')
    for e in sorted(meta_events, key=lambda x: x.timestamp, reverse=True)[:3]:
        params = e.params_json
        print(f'  [OK] {e.event_name.value}')
        print(f'     Campaign: {params.get(\"utm_campaign\", \"N/A\")}')
        print(f'     Content: {params.get(\"utm_content\", \"N/A\")}')
        print('')
"@

$results = python -c $checkScript
Write-Host $results

# Summary
Write-Host ""
Write-Host "[4/4] Summary" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan

$afterCount = ($results -split "`n" | Where-Object { $_ -match "^Total events:" }) -replace "Total events: ", ""
$googleCount = ($results -split "`n" | Where-Object { $_ -match "^Google events:" }) -replace "Google events: ", ""
$metaCount = ($results -split "`n" | Where-Object { $_ -match "^Meta events:" }) -replace "Meta events: ", ""

if ([int]$googleCount -gt 0) {
    Write-Host "✅ Google Ads tracking confirmed!" -ForegroundColor Green
    Write-Host "   Found $googleCount events with utm_source=google" -ForegroundColor Green
} else {
    Write-Host "⚠️  No Google Ads events found" -ForegroundColor Yellow
    Write-Host "   Test with: $googleUrl" -ForegroundColor White
}

if ([int]$metaCount -gt 0) {
    Write-Host "✅ Meta Ads tracking confirmed!" -ForegroundColor Green
    Write-Host "   Found $metaCount events with utm_source=facebook/meta" -ForegroundColor Green
} else {
    Write-Host "⚠️  No Meta Ads events found" -ForegroundColor Yellow
    Write-Host "   Test with: $metaUrl" -ForegroundColor White
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Configure UTM parameters in your ad platforms" -ForegroundColor White
Write-Host "  2. Verify UTM policy matches your ad setup" -ForegroundColor White
Write-Host "  3. Check events in admin console after real ad clicks" -ForegroundColor White
