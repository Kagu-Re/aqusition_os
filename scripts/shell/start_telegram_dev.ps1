# PowerShell script to start Telegram bot development environment
# Usage: .\start_telegram_dev.ps1

Write-Host "Telegram Bot Development Environment" -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Cyan
Write-Host ""

# Check if ngrok is available
$ngrokAvailable = Get-Command ngrok -ErrorAction SilentlyContinue
if (-not $ngrokAvailable) {
    Write-Host "⚠️  ngrok not found!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please install ngrok:" -ForegroundColor Yellow
    Write-Host "  1. Download from: https://ngrok.com/download" -ForegroundColor White
    Write-Host "  2. Extract ngrok.exe to a folder in your PATH" -ForegroundColor White
    Write-Host "  3. Or use: choco install ngrok" -ForegroundColor White
    Write-Host ""
    Write-Host "Alternative: Use localtunnel or cloudflared" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# Check if port 8001 is already in use
$portInUse = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "⚠️  Port 8001 is already in use!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Checking what's using it..." -ForegroundColor Yellow
    $process = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue | 
        Select-Object -ExpandProperty OwningProcess -Unique
    if ($process) {
        $processInfo = Get-Process -Id $process -ErrorAction SilentlyContinue
        if ($processInfo) {
            Write-Host "  Process ID: $($processInfo.Id)" -ForegroundColor White
            Write-Host "  Process Name: $($processInfo.ProcessName)" -ForegroundColor White
            Write-Host ""
            $kill = Read-Host "Kill this process? (Y/N)"
            if ($kill -eq 'Y' -or $kill -eq 'y') {
                Stop-Process -Id $processInfo.Id -Force
                Write-Host "✅ Process killed. Waiting 2 seconds..." -ForegroundColor Green
                Start-Sleep -Seconds 2
            } else {
                Write-Host "Please stop the process manually or use a different port." -ForegroundColor Yellow
                exit 1
            }
        }
    }
}

# Set PYTHONPATH
$env:PYTHONPATH = "src"

# Start Public API Server in background
Write-Host "[1/3] Starting Public API server on http://localhost:8001..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Public API Server' -ForegroundColor Cyan; Write-Host 'URL: http://localhost:8001' -ForegroundColor Green; Write-Host ''; `$env:PYTHONPATH='src'; python -m ae.cli run-public --host 127.0.0.1 --port 8001"

# Wait for server to start
Write-Host "[2/3] Waiting for server to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Test server
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✅ Server is running!" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Server may not be ready yet. Check the server window." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[3/3] Starting ngrok tunnel..." -ForegroundColor Green

# Check if ngrok is already running
$ngrokRunning = Get-Process -Name "ngrok" -ErrorAction SilentlyContinue
if ($ngrokRunning) {
    Write-Host ""
    Write-Host "⚠️  ngrok is already running!" -ForegroundColor Yellow
    Write-Host "  Found $($ngrokRunning.Count) process(es)" -ForegroundColor White
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Cyan
    Write-Host "  1. Stop existing ngrok: .\stop_ngrok.ps1" -ForegroundColor White
    Write-Host "  2. Use existing tunnel (check http://localhost:4040)" -ForegroundColor White
    Write-Host "  3. Start with different port: ngrok http 8002" -ForegroundColor White
    Write-Host ""
    $choice = Read-Host "Stop existing ngrok and start new? (Y/N)"
    if ($choice -eq 'Y' -or $choice -eq 'y') {
        foreach ($proc in $ngrokRunning) {
            Stop-Process -Id $proc.Id -Force
        }
        Write-Host "✅ Stopped existing ngrok. Waiting 2 seconds..." -ForegroundColor Green
        Start-Sleep -Seconds 2
    } else {
        Write-Host ""
        Write-Host "Using existing ngrok tunnel. Check http://localhost:4040 for URL." -ForegroundColor Cyan
        Write-Host ""
        Write-Host "📋 Next steps:" -ForegroundColor Cyan
        Write-Host "  1. Get HTTPS URL from http://localhost:4040" -ForegroundColor White
        Write-Host "  2. Set webhook using that URL" -ForegroundColor White
        Write-Host ""
        exit 0
    }
}

Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host '  1. Copy the HTTPS URL from ngrok (e.g., https://abc123.ngrok-free.app)' -ForegroundColor White
Write-Host "  2. Set webhook using:" -ForegroundColor White
Write-Host ""
Write-Host '     curl -X POST "https://api.telegram.org/bot8149020202:AAHeyDXCBvrRYnWYq_Z-1Z0IFJDkpc97A20/setWebhook" \' -ForegroundColor Gray
Write-Host '       -H "Content-Type: application/json" \' -ForegroundColor Gray
Write-Host '       -d ''{"url": "https://YOUR_NGROK_URL/api/v1/telegram/webhook?db=acq.db"}''' -ForegroundColor Gray
Write-Host ""
Write-Host '  3. Or use: python setup_telegram_webhook.py (update WEBHOOK_URL first)' -ForegroundColor White
Write-Host ""
Write-Host "  4. Send a message to @massage_thaibot on Telegram to test" -ForegroundColor White
Write-Host ""
Write-Host "📊 ngrok dashboard: http://localhost:4040" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop ngrok" -ForegroundColor Yellow
Write-Host ""

# Start ngrok
ngrok http 8001
