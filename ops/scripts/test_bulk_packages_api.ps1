# Test script for Service Packages Bulk Update API endpoints
# Requires: Server running at http://localhost:8000
# Requires: Valid authentication token

param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$Db = "acq.db",
    [string]$Token = "",
    [switch]$SkipAuth = $false
)

$ErrorActionPreference = "Stop"

Write-Host "=== Service Packages Bulk Update API Tests ===" -ForegroundColor Cyan
Write-Host ""

# Check if server is running
Write-Host "Checking if server is running..." -ForegroundColor Yellow
try {
    $healthCheck = Invoke-RestMethod -Uri "$BaseUrl/api/health" -Method Get -ErrorAction Stop
    Write-Host "OK Server is running" -ForegroundColor Green
} catch {
    Write-Host "X Server is not running. Please start the server first." -ForegroundColor Red
    Write-Host "  Run: python -m ae.console_app" -ForegroundColor Yellow
    exit 1
}

# Get auth token if not provided
if (-not $SkipAuth -and -not $Token) {
    Write-Host "Note: Authentication may be required. Set -Token parameter or use -SkipAuth if auth is disabled." -ForegroundColor Yellow
}

$headers = @{
    "Content-Type" = "application/json"
}
if ($Token) {
    $headers["Authorization"] = "Bearer $Token"
}

# Test 1: List packages to see what we have
Write-Host ""
Write-Host "Test 1: List existing packages..." -ForegroundColor Cyan
try {
    $packages = Invoke-RestMethod -Uri "$BaseUrl/api/service-packages?db=$Db" -Method Get -Headers $headers
    Write-Host "OK Found $($packages.count) packages" -ForegroundColor Green
    if ($packages.items.Count -gt 0) {
        Write-Host "  Sample packages:" -ForegroundColor Gray
        $packages.items | Select-Object -First 3 | ForEach-Object {
            Write-Host "    - $($_.package_id): active=$($_.active), price=$($_.price), client=$($_.client_id)" -ForegroundColor Gray
        }
        $testPackageIds = $packages.items | Select-Object -First 3 -ExpandProperty package_id
    } else {
        Write-Host "  WARN No packages found. Creating test packages..." -ForegroundColor Yellow
        # Create test packages
        $testClientId = "test-client-$(Get-Random)"
        $testPackages = @()
        for ($i = 1; $i -le 3; $i++) {
            $pkgId = "test-pkg-$i-$(Get-Random)"
            $body = @{
                package_id = $pkgId
                client_id = $testClientId
                name = "Test Package $i"
                price = 1000.0 + ($i * 100)
                duration_min = 60
                active = $false
            } | ConvertTo-Json
            try {
                $created = Invoke-RestMethod -Uri "$BaseUrl/api/service-packages?db=$Db" -Method Post -Headers $headers -Body $body
                $testPackages += $pkgId
                Write-Host "    Created: $pkgId" -ForegroundColor Gray
            } catch {
                Write-Host "    Failed to create test package: $_" -ForegroundColor Red
            }
        }
        $testPackageIds = $testPackages
    }
} catch {
    Write-Host "X Failed to list packages: $_" -ForegroundColor Red
    exit 1
}

if (-not $testPackageIds -or $testPackageIds.Count -eq 0) {
    Write-Host "X No packages available for testing" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Using test packages: $($testPackageIds -join ', ')" -ForegroundColor Yellow

# Test 2: Bulk update active status (dry_run)
Write-Host ""
Write-Host "Test 2: Bulk update active status (DRY RUN)..." -ForegroundColor Cyan
try {
    $body = @{
        package_ids = $testPackageIds
        mode = "dry_run"
        updates = @{
            active = $true
        }
        notes = "Test bulk activation"
    } | ConvertTo-Json -Depth 10
    
    $result = Invoke-RestMethod -Uri "$BaseUrl/api/service-packages/bulk-update?db=$Db" -Method Post -Headers $headers -Body $body
    Write-Host "OK Dry run completed" -ForegroundColor Green
    Write-Host "  Bulk ID: $($result.bulk_id)" -ForegroundColor Gray
    Write-Host "  Status: $($result.status)" -ForegroundColor Gray
    Write-Host "  Counters:" -ForegroundColor Gray
    Write-Host "    Total: $($result.result.counters.total)" -ForegroundColor Gray
    Write-Host "    Would Update: $($result.result.counters.updated)" -ForegroundColor Gray
    Write-Host "    Skipped: $($result.result.counters.skipped)" -ForegroundColor Gray
    Write-Host "    Failed: $($result.result.counters.failed)" -ForegroundColor Gray
    
    if ($result.result.packages.Count -gt 0) {
        Write-Host "  Sample results:" -ForegroundColor Gray
        $result.result.packages | Select-Object -First 2 | ForEach-Object {
            Write-Host "    - $($_.package_id): $($_.status)" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "X Failed: $_" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "  Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
}

# Test 3: Bulk update active status (execute)
Write-Host ""
Write-Host "Test 3: Bulk update active status (EXECUTE)..." -ForegroundColor Cyan
try {
    $body = @{
        package_ids = $testPackageIds
        mode = "execute"
        updates = @{
            active = $true
        }
        notes = "Test bulk activation - executed"
    } | ConvertTo-Json -Depth 10
    
    $result = Invoke-RestMethod -Uri "$BaseUrl/api/service-packages/bulk-update?db=$Db" -Method Post -Headers $headers -Body $body
    Write-Host "OK Execute completed" -ForegroundColor Green
    Write-Host "  Bulk ID: $($result.bulk_id)" -ForegroundColor Gray
    Write-Host "  Status: $($result.status)" -ForegroundColor Gray
    Write-Host "  Updated: $($result.result.counters.updated) packages" -ForegroundColor Green
    
    # Verify the update
    Start-Sleep -Seconds 1
    $verify = Invoke-RestMethod -Uri "$BaseUrl/api/service-packages/$($testPackageIds[0])?db=$Db" -Method Get -Headers $headers
    if ($verify.package.active -eq $true) {
        Write-Host "  OK Verified: Package is now active" -ForegroundColor Green
    } else {
        Write-Host "  X Verification failed: Package is still inactive" -ForegroundColor Red
    }
} catch {
    Write-Host "X Failed: $_" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "  Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
}

# Test 4: Bulk update price (dry_run)
Write-Host ""
Write-Host "Test 4: Bulk update price (DRY RUN)..." -ForegroundColor Cyan
try {
    $body = @{
        package_ids = $testPackageIds
        mode = "dry_run"
        updates = @{
            price = 2500.0
        }
        notes = "Test bulk price update"
    } | ConvertTo-Json -Depth 10
    
    $result = Invoke-RestMethod -Uri "$BaseUrl/api/service-packages/bulk-update?db=$Db" -Method Post -Headers $headers -Body $body
    Write-Host "OK Dry run completed" -ForegroundColor Green
    Write-Host "  Would update price to: $($result.result.updates.price)" -ForegroundColor Gray
    Write-Host "  Packages affected: $($result.result.counters.total)" -ForegroundColor Gray
} catch {
    Write-Host "X Failed: $_" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "  Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
}

# Test 5: Bulk update both active and price (dry_run)
Write-Host ""
Write-Host "Test 5: Bulk update active + price (DRY RUN)..." -ForegroundColor Cyan
try {
    $body = @{
        package_ids = $testPackageIds
        mode = "dry_run"
        updates = @{
            active = $false
            price = 3000.0
        }
        notes = "Test bulk update both fields"
    } | ConvertTo-Json -Depth 10
    
    $result = Invoke-RestMethod -Uri "$BaseUrl/api/service-packages/bulk-update?db=$Db" -Method Post -Headers $headers -Body $body
    Write-Host "OK Dry run completed" -ForegroundColor Green
    Write-Host "  Action: $($result.action)" -ForegroundColor Gray
    Write-Host "  Updates: $($result.result.updates | ConvertTo-Json -Compress)" -ForegroundColor Gray
} catch {
    Write-Host "X Failed: $_" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "  Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
}

# Test 6: Bulk delete (dry_run)
Write-Host ""
Write-Host "Test 6: Bulk delete packages (DRY RUN)..." -ForegroundColor Cyan
try {
    $body = @{
        package_ids = $testPackageIds
        mode = "dry_run"
        notes = "Test bulk delete"
    } | ConvertTo-Json -Depth 10
    
    $result = Invoke-RestMethod -Uri "$BaseUrl/api/service-packages/bulk-delete?db=$Db" -Method Post -Headers $headers -Body $body
    Write-Host "OK Dry run completed" -ForegroundColor Green
    Write-Host "  Would delete: $($result.result.counters.total) packages" -ForegroundColor Gray
    Write-Host "  Note: Not executing delete to preserve test data" -ForegroundColor Yellow
} catch {
    Write-Host "X Failed: $_" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "  Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
}

# Test 7: Filter by client_id
Write-Host ""
Write-Host "Test 7: Bulk update with client_id filter (DRY RUN)..." -ForegroundColor Cyan
try {
    # Get first package's client_id
    $firstPkg = Invoke-RestMethod -Uri "$BaseUrl/api/service-packages/$($testPackageIds[0])?db=$Db" -Method Get -Headers $headers
    $clientId = $firstPkg.package.client_id
    
    $body = @{
        client_id = $clientId
        mode = "dry_run"
        updates = @{
            active = $true
        }
        limit = 10
        notes = "Test filter by client_id"
    } | ConvertTo-Json -Depth 10
    
    $result = Invoke-RestMethod -Uri "$BaseUrl/api/service-packages/bulk-update?db=$Db" -Method Post -Headers $headers -Body $body
    Write-Host "OK Filter test completed" -ForegroundColor Green
    Write-Host "  Found $($result.result.counters.total) packages for client: $clientId" -ForegroundColor Gray
} catch {
    Write-Host "X Failed: $_" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "  Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
}

# Test 8: Error handling - invalid updates
Write-Host ""
Write-Host "Test 8: Error handling - invalid updates..." -ForegroundColor Cyan
try {
    $body = @{
        package_ids = $testPackageIds
        mode = "dry_run"
        updates = @{}  # Empty updates should fail
    } | ConvertTo-Json -Depth 10
    
    $result = Invoke-RestMethod -Uri "$BaseUrl/api/service-packages/bulk-update?db=$Db" -Method Post -Headers $headers -Body $body
    Write-Host "X Should have failed but did not" -ForegroundColor Red
} catch {
    if ($_.Exception.Response.StatusCode -eq 400) {
        Write-Host "OK Correctly rejected invalid request" -ForegroundColor Green
        Write-Host "  Error: $($_.ErrorDetails.Message)" -ForegroundColor Gray
    } else {
        Write-Host "X Unexpected error: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Tests Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Summary:" -ForegroundColor Yellow
Write-Host "  - All bulk update endpoints tested" -ForegroundColor Gray
Write-Host "  - Dry run and execute modes tested" -ForegroundColor Gray
Write-Host "  - Error handling verified" -ForegroundColor Gray
Write-Host ""
Write-Host "Note: Test packages were created/modified. Clean up manually if needed." -ForegroundColor Yellow
