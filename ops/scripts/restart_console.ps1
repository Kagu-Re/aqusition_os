# Restart Console Server Script
# Stops any existing console server on port 8000 and starts a new one

param(
    [int]$Port = 8000,
    [string]$HostName = "127.0.0.1"
)

Write-Host "=== Restarting Console Server ===" -ForegroundColor Cyan
Write-Host ""

# Find and stop existing processes on port 8000
Write-Host "Checking for existing server on port $Port..." -ForegroundColor Yellow
$connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($connections) {
    foreach ($conn in $connections) {
        $processId = $conn.OwningProcess
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "Stopping process $processId ($($process.ProcessName))..." -ForegroundColor Yellow
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 2
    Write-Host "[OK] Stopped existing server" -ForegroundColor Green
} else {
    Write-Host "No existing server found on port $Port" -ForegroundColor Gray
}

# Wait a moment for port to be released
Start-Sleep -Seconds 1

# Start new server
Write-Host ""
Write-Host "Starting new console server..." -ForegroundColor Yellow
$env:PYTHONPATH = "src"

# Start process in a new window so it stays running after script exits
$processInfo = New-Object System.Diagnostics.ProcessStartInfo
$processInfo.FileName = "python"
$processInfo.Arguments = "-m ae.cli serve-console --host $HostName --port $Port"
$processInfo.UseShellExecute = $true
$processInfo.CreateNoWindow = $false
$processInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Normal
$process = [System.Diagnostics.Process]::Start($processInfo)

Write-Host "[OK] Server started (PID: $($process.Id))" -ForegroundColor Green
Write-Host ""
Write-Host "Console available at: http://${HostName}:${Port}" -ForegroundColor Cyan
Write-Host "Server is running in a separate window. Close that window to stop the server." -ForegroundColor Gray
Write-Host ""

# Wait a moment and check if it's running
Start-Sleep -Seconds 3
try {
    $response = Invoke-RestMethod -Uri "http://${HostName}:${Port}/api/health" -Method Get -TimeoutSec 2
    Write-Host "[OK] Server is healthy and responding" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Server may still be starting up..." -ForegroundColor Yellow
}
