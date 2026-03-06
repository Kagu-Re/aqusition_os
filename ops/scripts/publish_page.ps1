# PowerShell script to publish a page step-by-step
# Usage: .\ops\scripts\publish_page.ps1 -PageId p1 -Db acq.db

param(
    [Parameter(Mandatory=$true)]
    [string]$PageId,
    
    [Parameter(Mandatory=$false)]
    [string]$Db = "acq.db"
)

$ErrorActionPreference = "Stop"

# Set PYTHONPATH
$env:PYTHONPATH = "src"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Page Publishing Walkthrough" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Record events
Write-Host "[1/4] Recording test events..." -ForegroundColor Yellow
$events = @("call_click", "quote_submit", "thank_you_view")

foreach ($event in $events) {
    Write-Host "  Recording $event..." -ForegroundColor Gray
    python -m ae.cli record-event --db $Db --page-id $PageId --event-name $event --params-json '{\"test\":true}'
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ Failed to record $event" -ForegroundColor Red
        exit 1
    }
}
Write-Host "  ✓ All events recorded" -ForegroundColor Green
Write-Host ""

# Step 2: Validate
Write-Host "[2/4] Validating page..." -ForegroundColor Yellow
python -m ae.cli validate-page --db $Db --page-id $PageId
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Validation failed" -ForegroundColor Red
    Write-Host "  Check errors above and fix before publishing" -ForegroundColor Yellow
    exit 1
}
Write-Host "  ✓ Validation passed" -ForegroundColor Green
Write-Host ""

# Step 3: Publish
Write-Host "[3/4] Publishing page..." -ForegroundColor Yellow
python -m ae.cli publish-page --db $Db --page-id $PageId
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Publish failed" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Page published successfully" -ForegroundColor Green
Write-Host ""

# Step 4: Verify output
Write-Host "[4/4] Verifying published file..." -ForegroundColor Yellow
$outputPath = "exports\static_site\$PageId\index.html"
if (Test-Path $outputPath) {
    $file = Get-Item $outputPath
    Write-Host "  ✓ Published file found" -ForegroundColor Green
    Write-Host "  Location: $($file.FullName)" -ForegroundColor Cyan
    Write-Host "  Size: $($file.Length) bytes" -ForegroundColor Gray
    Write-Host "  Modified: $($file.LastWriteTime)" -ForegroundColor Gray
} else {
    Write-Host "  ⚠ Published file not found at: $outputPath" -ForegroundColor Yellow
    Write-Host "  Check if publish succeeded" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Publishing Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Open: $outputPath" -ForegroundColor White
Write-Host "  2. Or serve with: cd exports\static_site\$PageId; python -m http.server 8080" -ForegroundColor White
Write-Host "  3. Then visit: http://localhost:8080/index.html" -ForegroundColor White
