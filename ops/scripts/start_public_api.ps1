# PowerShell script to start the Public API server
# Usage: .\ops\scripts\start_public_api.ps1

Write-Host "Starting Public API server..." -ForegroundColor Green
Write-Host "API will be available at: http://localhost:8001" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Set PYTHONPATH
$env:PYTHONPATH = "src"

# Start the server
python -m ae.cli run-public --host 127.0.0.1 --port 8001
