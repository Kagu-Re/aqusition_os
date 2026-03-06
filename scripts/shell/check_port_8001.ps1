# Check what's using port 8001 and optionally kill it
# Usage: .\check_port_8001.ps1 [-Kill]

param(
    [switch]$Kill
)

Write-Host "Checking port 8001..." -ForegroundColor Cyan

# Find process using port 8001
$process = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue | 
    Select-Object -ExpandProperty OwningProcess -Unique

if ($process) {
    $processInfo = Get-Process -Id $process -ErrorAction SilentlyContinue
    if ($processInfo) {
        Write-Host "Port 8001 is in use by:" -ForegroundColor Yellow
        Write-Host "  Process ID: $($processInfo.Id)" -ForegroundColor White
        Write-Host "  Process Name: $($processInfo.ProcessName)" -ForegroundColor White
        Write-Host "  Command Line: $($processInfo.Path)" -ForegroundColor Gray
        
        if ($Kill) {
            Write-Host ""
            Write-Host "Killing process $($processInfo.Id)..." -ForegroundColor Yellow
            Stop-Process -Id $processInfo.Id -Force
            Write-Host "✅ Process killed!" -ForegroundColor Green
            Start-Sleep -Seconds 2
        } else {
            Write-Host ""
            Write-Host "To kill this process, run:" -ForegroundColor Cyan
            Write-Host "  .\check_port_8001.ps1 -Kill" -ForegroundColor White
            Write-Host ""
            Write-Host "Or manually:" -ForegroundColor Cyan
            Write-Host "  Stop-Process -Id $($processInfo.Id) -Force" -ForegroundColor White
        }
    }
} else {
    Write-Host "✅ Port 8001 is available!" -ForegroundColor Green
}
