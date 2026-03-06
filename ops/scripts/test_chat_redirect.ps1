# Test Chat Redirect Functionality
# This script helps verify that quote-to-chat flow is working correctly

param(
    [string]$ClientId = "",
    [string]$DbPath = "acq.db",
    [string]$PublicApiUrl = "http://localhost:8001"
)

Write-Host "=== Testing Chat Redirect Functionality ===" -ForegroundColor Cyan
Write-Host ""

if (-not $ClientId) {
    Write-Host "Usage: .\test_chat_redirect.ps1 -ClientId YOUR_CLIENT_ID [-DbPath acq.db] [-PublicApiUrl http://localhost:8001]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Example:" -ForegroundColor Yellow
    Write-Host "  .\test_chat_redirect.ps1 -ClientId demo1" -ForegroundColor Gray
    exit 1
}

Write-Host "1. Testing Chat Channel API..." -ForegroundColor Cyan
$apiUrl = "$PublicApiUrl/v1/chat/channel?client_id=$ClientId&db=$DbPath"
Write-Host "   URL: $apiUrl" -ForegroundColor Gray

try {
    $response = Invoke-RestMethod -Uri $apiUrl -Method Get -ErrorAction Stop
    Write-Host "   [OK] Chat channel found!" -ForegroundColor Green
    Write-Host ""
    Write-Host "   Channel Details:" -ForegroundColor Yellow
    Write-Host "     Channel ID: $($response.channel_id)" -ForegroundColor Gray
    Write-Host "     Provider: $($response.provider)" -ForegroundColor Gray
    Write-Host "     Handle: $($response.handle)" -ForegroundColor Gray
    Write-Host "     Display Name: $($response.display_name)" -ForegroundColor Gray
    Write-Host "     Chat URL: $($response.chat_url)" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "2. Next Steps:" -ForegroundColor Cyan
    Write-Host "   a) Publish your page (if not already published):" -ForegroundColor Yellow
    Write-Host "      python -m ae.cli publish-page --db $DbPath --page-id p-$ClientId-v1" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   b) Open the published HTML page in a browser" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   c) Open browser DevTools (F12) → Network tab" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   d) Click 'Get a quote' button" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   e) Verify:" -ForegroundColor Yellow
    Write-Host "      - Event is sent to /v1/event with event_name: 'quote_submit'" -ForegroundColor Gray
    Write-Host "      - Page redirects to: $($response.chat_url)" -ForegroundColor Gray
    Write-Host ""
    
} catch {
    Write-Host "   [ERROR] Failed to fetch chat channel" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    
    if ($_.Exception.Response.StatusCode -eq 404) {
        Write-Host "   Solution: Register a chat channel for this client:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "   curl -X POST http://localhost:8000/api/chat/channels?db=$DbPath \" -ForegroundColor Gray
        Write-Host "     -H 'Content-Type: application/json' \" -ForegroundColor Gray
        Write-Host "     -d '{`"channel_id`": `"ch_$ClientId`_whatsapp`", `"provider`": `"whatsapp`", `"handle`": `"+66-80-123-4567`", `"display_name`": `"Test WhatsApp`", `"meta_json`": {`"client_id`": `"$ClientId`"}}'" -ForegroundColor Gray
        Write-Host ""
    } else {
        Write-Host "   Check that:" -ForegroundColor Yellow
        Write-Host "     - Public API server is running on $PublicApiUrl" -ForegroundColor Gray
        Write-Host "     - Database path is correct: $DbPath" -ForegroundColor Gray
        Write-Host "     - Client ID exists: $ClientId" -ForegroundColor Gray
    }
    exit 1
}

Write-Host "=== Test Complete ===" -ForegroundColor Cyan
