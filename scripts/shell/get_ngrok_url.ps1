# Get the current ngrok URL from the ngrok API
# Usage: .\get_ngrok_url.ps1

Write-Host "Fetching ngrok tunnel URL..." -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -ErrorAction Stop
    
    if ($response.tunnels -and $response.tunnels.Count -gt 0) {
        $httpsTunnel = $response.tunnels | Where-Object { $_.proto -eq "https" } | Select-Object -First 1
        
        if ($httpsTunnel) {
            Write-Host ""
            Write-Host "✅ ngrok HTTPS URL:" -ForegroundColor Green
            Write-Host "   $($httpsTunnel.public_url)" -ForegroundColor White
            Write-Host ""
            Write-Host "Webhook URL:" -ForegroundColor Cyan
            $webhookUrl = "$($httpsTunnel.public_url)/api/v1/telegram/webhook?db=acq.db"
            Write-Host "   $webhookUrl" -ForegroundColor White
            Write-Host ""
            Write-Host "To set webhook, run:" -ForegroundColor Cyan
            Write-Host "   curl -X POST `"https://api.telegram.org/bot8149020202:AAHeyDXCBvrRYnWYq_Z-1Z0IFJDkpc97A20/setWebhook`" \" -ForegroundColor Gray
            Write-Host "     -H `"Content-Type: application/json`" \" -ForegroundColor Gray
            Write-Host "     -d '{\"url\": \"$webhookUrl\"}'" -ForegroundColor Gray
            Write-Host ""
            
            # Copy to clipboard if available
            try {
                Set-Clipboard -Value $webhookUrl
                Write-Host "✅ Webhook URL copied to clipboard!" -ForegroundColor Green
            } catch {
                # Clipboard not available, that's okay
            }
        } else {
            Write-Host "⚠️  No HTTPS tunnel found. Only HTTP tunnels available." -ForegroundColor Yellow
        }
    } else {
        Write-Host "⚠️  No tunnels found. Is ngrok running?" -ForegroundColor Yellow
        Write-Host "   Start ngrok: ngrok http 8001" -ForegroundColor White
    }
} catch {
    Write-Host "❌ Could not connect to ngrok API." -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Make sure:" -ForegroundColor Cyan
    Write-Host "  1. ngrok is running" -ForegroundColor White
    Write-Host "     Run: .\start_ngrok.ps1" -ForegroundColor Gray
    Write-Host "     Or: ngrok http 8001" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  2. ngrok API is accessible at http://localhost:4040" -ForegroundColor White
    Write-Host "     Check: http://localhost:4040" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Quick fix:" -ForegroundColor Cyan
    Write-Host "  .\start_ngrok.ps1" -ForegroundColor White
}
