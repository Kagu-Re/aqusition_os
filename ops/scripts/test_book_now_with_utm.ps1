# Test "Book now" Flow with Google/Meta UTM Parameters
# This script tests the full attribution flow with realistic ad campaign parameters

Write-Host "=== Testing Book Now Flow with UTM Parameters ===" -ForegroundColor Cyan
Write-Host ""

# Test URLs with Google Ads UTM parameters
$googleAdsUrl = "http://localhost:8080/p1/index.html?utm_source=google&utm_medium=cpc&utm_campaign=plumber-brisbane-feb2026&utm_term=emergency+plumber&utm_content=ad-headline-a"

# Test URLs with Meta Ads UTM parameters  
$metaAdsUrl = "http://localhost:8080/p1/index.html?utm_source=facebook&utm_medium=social&utm_campaign=plumber-brisbane-feb2026&utm_content=video-ad-v1"

Write-Host "Test URLs:" -ForegroundColor Yellow
Write-Host ""
Write-Host "Google Ads:" -ForegroundColor Green
Write-Host "  $googleAdsUrl" -ForegroundColor White
Write-Host ""
Write-Host "Meta Ads:" -ForegroundColor Green
Write-Host "  $metaAdsUrl" -ForegroundColor White
Write-Host ""

# Check if servers are running
Write-Host "Checking servers..." -ForegroundColor Cyan
try {
    $apiCheck = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✅ Public API: Running" -ForegroundColor Green
} catch {
    Write-Host "❌ Public API: Not running (start with: python -m ae.cli run-public --port 8001)" -ForegroundColor Red
    exit 1
}

try {
    $httpCheck = Invoke-WebRequest -Uri "http://localhost:8080" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✅ HTTP Server: Running" -ForegroundColor Green
} catch {
    Write-Host "❌ HTTP Server: Not running (start with: python -m http.server 8080 in exports/static_site)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Testing Instructions ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Open browser DevTools (F12) → Network tab" -ForegroundColor White
Write-Host ""
Write-Host "2. Test Google Ads Attribution:" -ForegroundColor Yellow
Write-Host "   - Open: $googleAdsUrl" -ForegroundColor White
Write-Host "   - Click 'Book now' button" -ForegroundColor White
Write-Host "   - Verify in Network tab:" -ForegroundColor White
Write-Host "     * POST /v1/event with utm_source=google" -ForegroundColor Gray
Write-Host "     * POST /lead with utm_source=google, utm_campaign=plumber-brisbane-feb2026" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Test Meta Ads Attribution:" -ForegroundColor Yellow
Write-Host "   - Open: $metaAdsUrl" -ForegroundColor White
Write-Host "   - Click 'Book now' button" -ForegroundColor White
Write-Host "   - Verify in Network tab:" -ForegroundColor White
Write-Host "     * POST /v1/event with utm_source=facebook" -ForegroundColor Gray
Write-Host "     * POST /lead with utm_source=facebook, utm_campaign=plumber-brisbane-feb2026" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Verify in Database:" -ForegroundColor Yellow
Write-Host "   Run this command to check UTM params:" -ForegroundColor White
Write-Host '   python -c "from ae import repo; leads = repo.list_leads(\"acq.db\"); recent = [l for l in leads if l.message and \"Booking request\" in l.message][-2:]; [print(f\"Lead {l.lead_id}: utm_source={l.utm_source}, utm_campaign={l.utm_campaign}, utm_medium={l.utm_medium}\") for l in recent]"' -ForegroundColor Gray
Write-Host ""
Write-Host "5. Verify in Console:" -ForegroundColor Yellow
Write-Host "   - Open: http://localhost:8000/console → Leads" -ForegroundColor White
Write-Host "   - Check that leads show UTM attribution data" -ForegroundColor White
Write-Host ""
Write-Host "=== Expected Results ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Event tracked with UTM params" -ForegroundColor Green
Write-Host "✅ Lead created with UTM params" -ForegroundColor Green
Write-Host "✅ UTM params preserved when creating booking" -ForegroundColor Green
Write-Host "✅ ROAS calculation can use UTM params" -ForegroundColor Green
Write-Host ""
Write-Host "Press any key to open Google Ads test URL..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Open browser with Google Ads URL
Start-Process $googleAdsUrl

Write-Host ""
Write-Host "Browser opened! Follow the testing instructions above." -ForegroundColor Green
