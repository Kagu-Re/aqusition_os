# Start ngrok tunnel for port 8001
# Usage: .\start_ngrok.ps1 [port]

param(
    [int]$Port = 8001
)

Write-Host "Starting ngrok tunnel..." -ForegroundColor Cyan
Write-Host "Port: $Port" -ForegroundColor White
Write-Host ""

# Check if ngrok is available
$ngrokAvailable = Get-Command ngrok -ErrorAction SilentlyContinue
if (-not $ngrokAvailable) {
    Write-Host "❌ ngrok not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install ngrok:" -ForegroundColor Yellow
    Write-Host "  1. Download from: https://ngrok.com/download" -ForegroundColor White
    Write-Host "  2. Extract ngrok.exe to a folder in your PATH" -ForegroundColor White
    Write-Host "  3. Or use: choco install ngrok" -ForegroundColor White
    exit 1
}

# Check if ngrok is already running
$ngrokRunning = Get-Process -Name "ngrok" -ErrorAction SilentlyContinue
if ($ngrokRunning) {
    Write-Host "⚠️  ngrok is already running!" -ForegroundColor Yellow
    Write-Host "  Found $($ngrokRunning.Count) process(es)" -ForegroundColor White
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Cyan
    Write-Host "  1. Stop existing: .\stop_ngrok.ps1" -ForegroundColor White
    Write-Host "  2. Get URL: .\get_ngrok_url.ps1" -ForegroundColor White
    Write-Host "  3. View dashboard: http://localhost:4040" -ForegroundColor White
    Write-Host ""
    $choice = Read-Host "Stop existing and start new? (Y/N)"
    if ($choice -eq 'Y' -or $choice -eq 'y') {
        foreach ($proc in $ngrokRunning) {
            Stop-Process -Id $proc.Id -Force
        }
        Write-Host "✅ Stopped existing ngrok. Waiting 2 seconds..." -ForegroundColor Green
        Start-Sleep -Seconds 2
    } else {
        Write-Host ""
        Write-Host "Using existing ngrok. Run .\get_ngrok_url.ps1 to get the URL." -ForegroundColor Cyan
        exit 0
    }
}

Write-Host "Starting ngrok tunnel on port $Port..." -ForegroundColor Green
Write-Host ""
Write-Host "📊 ngrok dashboard: http://localhost:4040" -ForegroundColor Cyan
Write-Host ""
Write-Host "Once started, run .\get_ngrok_url.ps1 in another terminal to get the URL" -ForegroundColor Yellow
Write-Host ""
Write-Host 'Press Ctrl+C to stop ngrok' -ForegroundColor Yellow
Write-Host ""

# Start ngrok
ngrok http $Port
