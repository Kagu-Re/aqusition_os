# Test Chat Redirect from Landing Page
# This script helps you test the quote-to-chat flow from a published HTML page

param(
    [string]$PageId = "p1",
    [string]$Port = "8080"
)

Write-Host "=== Testing Chat Redirect from Landing Page ===" -ForegroundColor Cyan
Write-Host ""

$pagePath = "exports/static_site/$PageId/index.html"

if (-not (Test-Path $pagePath)) {
    Write-Host "❌ Page not found: $pagePath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please publish the page first:" -ForegroundColor Yellow
    Write-Host "  `$env:PYTHONPATH='src'" -ForegroundColor Gray
    Write-Host "  python -m ae.cli publish-page --db acq.db --page-id $PageId" -ForegroundColor Gray
    exit 1
}

Write-Host "✅ Page found: $pagePath" -ForegroundColor Green
Write-Host ""

# Check if chat redirect code is present
$htmlContent = Get-Content $pagePath -Raw
if ($htmlContent -match "chatUrl|CLIENT_ID|chat/channel") {
    Write-Host "✅ Chat redirect JavaScript detected in HTML" -ForegroundColor Green
} else {
    Write-Host "⚠️  Chat redirect JavaScript NOT found - page may need republishing" -ForegroundColor Yellow
    Write-Host "   Republish with: python -m ae.cli publish-page --db acq.db --page-id $PageId" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== Starting Local HTTP Server ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting server on port $Port..." -ForegroundColor Yellow
Write-Host ""
Write-Host "📋 Instructions:" -ForegroundColor Cyan
Write-Host "   1. Server will start in the background" -ForegroundColor White
Write-Host "   2. Open your browser to: http://localhost:$Port/$PageId/index.html" -ForegroundColor Green
Write-Host "   3. Open DevTools (F12) → Network tab" -ForegroundColor White
Write-Host "   4. Click the 'Get a quote' button" -ForegroundColor White
Write-Host "   5. Verify:" -ForegroundColor White
Write-Host "      - Event sent to /v1/event with event_name: quote_submit" -ForegroundColor Gray
Write-Host "      - Request to /v1/chat/channel (on page load)" -ForegroundColor Gray
Write-Host "      - Page redirects to Telegram: https://t.me/reminortokkatta" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to stop the server when done" -ForegroundColor Yellow
Write-Host ""

# Start HTTP server
$serverPath = Resolve-Path "exports/static_site"
Set-Location $serverPath
python -m http.server $Port
