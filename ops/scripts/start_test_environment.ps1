# Start Test Environment
# Launches all services needed for testing the quote-to-chat flow

Write-Host "=== Starting Test Environment ===" -ForegroundColor Cyan
Write-Host ""

# Check if public API is already running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 1 -ErrorAction Stop
    Write-Host "⚠️  Public API already running on port 8001" -ForegroundColor Yellow
} catch {
    Write-Host "Starting Public API server (port 8001)..." -ForegroundColor Green
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "Write-Host '=== Public API Server (Port 8001) ===' -ForegroundColor Cyan; Write-Host ''; `$env:PYTHONPATH='src'; python -m ae.cli run-public --host 127.0.0.1 --port 8001"
    ) -WindowStyle Normal
    Start-Sleep -Seconds 2
}

# Check if HTTP server is already running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080/p1/index.html" -TimeoutSec 1 -ErrorAction Stop
    Write-Host "⚠️  HTTP server already running on port 8080" -ForegroundColor Yellow
} catch {
    Write-Host "Starting HTTP server for landing pages (port 8080)..." -ForegroundColor Green
    $staticPath = Resolve-Path "exports/static_site"
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "Write-Host '=== HTTP Server for Landing Pages (Port 8080) ===' -ForegroundColor Cyan; Write-Host ''; Write-Host 'Open: http://localhost:8080/p1/index.html' -ForegroundColor Green; Write-Host ''; Set-Location '$staticPath'; python -m http.server 8080"
    ) -WindowStyle Normal
    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Host "=== Services Started ===" -ForegroundColor Green
Write-Host ""
Write-Host "✅ Public API: http://localhost:8001" -ForegroundColor Green
Write-Host "   - Chat channel endpoint: /v1/chat/channel" -ForegroundColor Gray
Write-Host "   - Event tracking: /v1/event" -ForegroundColor Gray
Write-Host ""
Write-Host "✅ HTTP Server: http://localhost:8080" -ForegroundColor Green
Write-Host "   - Landing page: http://localhost:8080/p1/index.html" -ForegroundColor Gray
Write-Host ""
Write-Host "=== Testing Instructions ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Open browser: http://localhost:8080/p1/index.html" -ForegroundColor White
Write-Host "2. Open DevTools (F12) → Network tab" -ForegroundColor White
Write-Host "3. Click 'Get a quote' button" -ForegroundColor White
Write-Host "4. Verify:" -ForegroundColor White
Write-Host "   - Request to /v1/chat/channel (on page load)" -ForegroundColor Gray
Write-Host "   - Request to /v1/event with event_name: quote_submit" -ForegroundColor Gray
Write-Host "   - Page redirects to: https://t.me/reminortokkatta" -ForegroundColor Gray
Write-Host ""
Write-Host "Press any key to verify services..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Verify services
Write-Host ""
Write-Host "=== Verifying Services ===" -ForegroundColor Cyan
Write-Host ""

try {
    $apiResponse = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✅ Public API: Running (Status $($apiResponse.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "❌ Public API: Not responding" -ForegroundColor Red
}

try {
    $httpResponse = Invoke-WebRequest -Uri "http://localhost:8080/p1/index.html" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✅ HTTP Server: Running (Status $($httpResponse.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "❌ HTTP Server: Not responding" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Ready for Testing ===" -ForegroundColor Green
