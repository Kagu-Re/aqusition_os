# Stop all running ngrok processes
# Usage: .\stop_ngrok.ps1

Write-Host "Stopping ngrok processes..." -ForegroundColor Cyan

# Find all ngrok processes
$ngrokProcesses = Get-Process -Name "ngrok" -ErrorAction SilentlyContinue

if ($ngrokProcesses) {
    Write-Host "Found $($ngrokProcesses.Count) ngrok process(es):" -ForegroundColor Yellow
    foreach ($proc in $ngrokProcesses) {
        Write-Host "  PID: $($proc.Id) - Started: $($proc.StartTime)" -ForegroundColor White
    }
    
    Write-Host ""
    $confirm = Read-Host "Kill all ngrok processes? (Y/N)"
    if ($confirm -eq 'Y' -or $confirm -eq 'y') {
        foreach ($proc in $ngrokProcesses) {
            Stop-Process -Id $proc.Id -Force
            Write-Host "✅ Killed process $($proc.Id)" -ForegroundColor Green
        }
        Write-Host ""
        Write-Host "✅ All ngrok processes stopped!" -ForegroundColor Green
        Start-Sleep -Seconds 2
    } else {
        Write-Host "Cancelled." -ForegroundColor Yellow
    }
} else {
    Write-Host "✅ No ngrok processes found!" -ForegroundColor Green
}
