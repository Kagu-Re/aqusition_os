# Quick script to check if public API is running
Write-Host "Checking Public API status..." -ForegroundColor Yellow
Write-Host ""

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 2 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Public API is running on port 8001" -ForegroundColor Green
        Write-Host "   Status: $($response.StatusCode)" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "You can now test event tracking!" -ForegroundColor Green
        exit 0
    }
} catch {
    Write-Host "❌ Public API is NOT running" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To start the public API:" -ForegroundColor Cyan
    Write-Host "  1. Open a NEW terminal" -ForegroundColor White
    Write-Host "  2. Run:" -ForegroundColor White
    Write-Host "     `$env:PYTHONPATH='src'" -ForegroundColor Green
    Write-Host "     python -m ae.cli run-public --host 127.0.0.1 --port 8001" -ForegroundColor Green
    Write-Host ""
    Write-Host "  3. Keep that terminal running" -ForegroundColor White
    Write-Host "  4. Then retry your test" -ForegroundColor White
    exit 1
}
