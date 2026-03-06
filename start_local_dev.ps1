# Unified local development server
# Serves: Console, Public API, Landing Pages, Telegram Bots (polling)
# Usage: .\start_local_dev.ps1

$ErrorActionPreference = "Stop"

Write-Host "Acquisition Engine - Local Development Server" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host ""

# Validate script is run from project root
if (-not (Test-Path "src\ae\local_dev_server.py")) {
    Write-Host "❌ Error: Script must be run from project root directory" -ForegroundColor Red
    Write-Host "   Current directory: $PWD" -ForegroundColor Yellow
    Write-Host "   Expected: Directory containing 'src\ae\local_dev_server.py'" -ForegroundColor Yellow
    exit 1
}

# Check Python installation
Write-Host "Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Error: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "   Please install Python 3.12+ and ensure it's in your PATH" -ForegroundColor Yellow
    exit 1
}

# Check Python version (require 3.12+)
$versionOutput = python --version 2>&1
if ($versionOutput -match "Python (\d+)\.(\d+)") {
    $major = [int]$matches[1]
    $minor = [int]$matches[2]
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 12)) {
        Write-Host "❌ Error: Python 3.12+ required, found $versionOutput" -ForegroundColor Red
        exit 1
    }
}

# Check for required Python packages
Write-Host "Checking Python dependencies..." -ForegroundColor Yellow
try {
    python -c "import uvicorn" 2>&1 | Out-Null
    Write-Host "✅ uvicorn found" -ForegroundColor Green
} catch {
    Write-Host "❌ Error: uvicorn is not installed" -ForegroundColor Red
    Write-Host "   Install with: pip install uvicorn" -ForegroundColor Yellow
    exit 1
}

try {
    python -c "import fastapi" 2>&1 | Out-Null
    Write-Host "✅ fastapi found" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Warning: fastapi not found (may cause issues)" -ForegroundColor Yellow
}

Write-Host ""

# Clear Python cache to prevent stale code issues
Write-Host "Clearing Python cache..." -ForegroundColor Yellow
Get-ChildItem -Path . -Include __pycache__ -Recurse -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path . -Include *.pyc -Recurse -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Write-Host "✅ Python cache cleared" -ForegroundColor Green
Write-Host ""

# Set PYTHONPATH
$env:PYTHONPATH = "src"

# Set database path (default)
if (-not $env:AE_DB_PATH) {
    $env:AE_DB_PATH = "acq.db"
}

# Ensure database directory exists
$dbDir = Split-Path -Path $env:AE_DB_PATH -Parent
if ($dbDir -and -not (Test-Path $dbDir)) {
    Write-Host "Creating database directory: $dbDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $dbDir -Force | Out-Null
}

# Set public API URL for landing pages
# For local dev server, routes are at root level (/v1/*), not /api/v1/*
# So we use http://localhost:8000 (without /api)
if (-not $env:AE_PUBLIC_API_URL) {
    $env:AE_PUBLIC_API_URL = "http://localhost:8000"
}

# Check Redis availability (optional)
Write-Host "Checking Redis availability..." -ForegroundColor Yellow
if ($env:AE_REDIS_URL) {
    Write-Host "  Redis URL configured: $env:AE_REDIS_URL" -ForegroundColor White
    Write-Host "  ✅ Distributed state management enabled" -ForegroundColor Green
} else {
    Write-Host "  Warning: Redis not configured - using in-memory state" -ForegroundColor Yellow
    Write-Host "     Set AE_REDIS_URL for multi-instance deployments" -ForegroundColor Gray
}
Write-Host ""

# Check for required setup scripts
Write-Host "Checking setup scripts..." -ForegroundColor Yellow
if (-not (Test-Path "scripts\setup\setup_demo1_client.py")) {
    Write-Host "⚠️  Warning: scripts\setup\setup_demo1_client.py not found" -ForegroundColor Yellow
} else {
    Write-Host "Setting up massage client and packages..." -ForegroundColor Yellow
    python scripts/setup/setup_demo1_client.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  Warning: Setup script had issues, but continuing..." -ForegroundColor Yellow
    } else {
        Write-Host "✅ Client setup completed" -ForegroundColor Green
    }
}

if (-not (Test-Path "scripts\runbooks\clear_stale_conversations.py")) {
    Write-Host "⚠️  Warning: scripts\runbooks\clear_stale_conversations.py not found" -ForegroundColor Yellow
} else {
    Write-Host "Clearing stale booking sessions..." -ForegroundColor Yellow
    python scripts/runbooks/clear_stale_conversations.py --db $env:AE_DB_PATH
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  Warning: Failed to clear stale conversations, but continuing..." -ForegroundColor Yellow
    } else {
        Write-Host "✅ Stale booking sessions cleared" -ForegroundColor Green
    }
}
Write-Host ""

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Database: $env:AE_DB_PATH" -ForegroundColor White
Write-Host "  Public API URL: $env:AE_PUBLIC_API_URL" -ForegroundColor White
if ($env:AE_REDIS_URL) {
    Write-Host "  Redis: $env:AE_REDIS_URL" -ForegroundColor White
}
Write-Host ""

# Check if port 8000 is available (with fallback methods)
Write-Host "Checking port 8000 availability..." -ForegroundColor Yellow
$portInUse = $false
$processId = $null

# Try Get-NetTCPConnection first (requires admin on some systems)
try {
    $portInUse = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
    if ($portInUse) {
        $processId = ($portInUse | Select-Object -ExpandProperty OwningProcess -Unique)[0]
    }
} catch {
    # Fallback: Use netstat
    try {
        $netstatOutput = netstat -ano | Select-String ":8000.*LISTENING"
        if ($netstatOutput) {
            $portInUse = $true
            if ($netstatOutput -match "\s+(\d+)$") {
                $processId = [int]$matches[1]
            }
        }
    } catch {
        Write-Host "⚠️  Warning: Could not check port status (continuing anyway)" -ForegroundColor Yellow
    }
}

if ($portInUse -and $processId) {
    Write-Host "⚠️  Port 8000 is already in use!" -ForegroundColor Yellow
    $processInfo = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($processInfo) {
        Write-Host "  Process ID: $($processInfo.Id)" -ForegroundColor White
        Write-Host "  Process Name: $($processInfo.ProcessName)" -ForegroundColor White
        Write-Host ""
        $kill = Read-Host "Kill this process? (Y/N)"
        if ($kill -eq 'Y' -or $kill -eq 'y') {
            try {
                Stop-Process -Id $processInfo.Id -Force
                Write-Host "✅ Process killed. Waiting 2 seconds..." -ForegroundColor Green
                Start-Sleep -Seconds 2
            } catch {
                Write-Host "❌ Error: Could not kill process. Please stop it manually." -ForegroundColor Red
                exit 1
            }
        } else {
            Write-Host "Please stop the process manually or use a different port." -ForegroundColor Yellow
            exit 1
        }
    } else {
        Write-Host "⚠️  Warning: Process not found, but port appears in use" -ForegroundColor Yellow
        Write-Host "   You may need to stop the process manually" -ForegroundColor Yellow
    }
} else {
    Write-Host "✅ Port 8000 is available" -ForegroundColor Green
}
Write-Host ""

Write-Host "Starting unified local development server..." -ForegroundColor Green
Write-Host ""
Write-Host "Services available:" -ForegroundColor Cyan
Write-Host "  Console:        http://localhost:8000/console" -ForegroundColor White
Write-Host "  Money Board:    http://localhost:8000/money-board" -ForegroundColor White
Write-Host "  Public API:     http://localhost:8000/api" -ForegroundColor White
Write-Host "  Landing Pages:  http://localhost:8000/pages/{page_id}" -ForegroundColor White
Write-Host "  Telegram Bots:  Polling mode (no webhook needed)" -ForegroundColor White
Write-Host ""
Write-Host "Telegram bots will start automatically in polling mode." -ForegroundColor Yellow
Write-Host "No ngrok needed - bots poll Telegram API directly." -ForegroundColor Yellow
Write-Host ""
if ($env:AE_REDIS_URL) {
    Write-Host "[OK] Distributed state: Enabled - Redis" -ForegroundColor Green
} else {
    Write-Host "[INFO] Distributed state: Disabled - single instance mode" -ForegroundColor Cyan
}
Write-Host ""
Write-Host "⚠️  Cache Prevention:" -ForegroundColor Yellow
Write-Host "  - Server sends no-cache headers for all static files" -ForegroundColor White
Write-Host "  - Python cache cleared on startup" -ForegroundColor White
Write-Host "  - For browser cache: Use Ctrl+Shift+R (hard refresh) or incognito mode" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start server with error handling
try {
    # Note: --reload disabled to prevent duplicate Telegram polling instances
    # Each reload creates a new process that tries to poll the same bot, causing 409 Conflict
    # For code changes, manually restart the server (Ctrl+C then re-run script)
    python -m uvicorn ae.local_dev_server:app --host 127.0.0.1 --port 8000
} catch {
    Write-Host ""
    Write-Host "Error starting server: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Ensure all dependencies are installed: pip install -r requirements.txt" -ForegroundColor White
    Write-Host "  2. Check that port 8000 is not in use by another process" -ForegroundColor White
    Write-Host "  3. Verify database path is correct - check AE_DB_PATH env var" -ForegroundColor White
    Write-Host "  4. Check Python version - requires 3.12 or higher" -ForegroundColor White
    exit 1
}
