@echo off
REM Service Package Flow Test - Startup Script
REM This script starts all required services for testing the package selection flow

echo ========================================
echo Service Package Flow Test - Startup
echo ========================================
echo.

REM Set PYTHONPATH
set PYTHONPATH=src

REM Check if database exists
if not exist "acq.db" (
    echo [ERROR] Database file acq.db not found!
    echo Please ensure the database exists before running tests.
    pause
    exit /b 1
)

echo [1/4] Checking database and test data...
python -c "from ae import repo; client = repo.get_client('acq.db', 'test-massage-spa'); print('[OK] Test client exists:', client.client_id)" 2>nul
if errorlevel 1 (
    echo [WARNING] Test client may not exist. Continuing anyway...
)

python -c "from ae import repo; packages = repo.list_packages('acq.db', client_id='test-massage-spa'); print('[OK] Found', len(packages), 'service packages')" 2>nul
if errorlevel 1 (
    echo [WARNING] Service packages may not exist. Continuing anyway...
)

echo.
echo [2/4] Starting public API server...
echo [INFO] This will run in a new window. Keep it running during tests.
echo [INFO] If API is already running, you can skip this step.
echo.
start "Public API Server" cmd /k "set PYTHONPATH=src && python -m ae.cli run-public --host 127.0.0.1 --port 8001"
timeout /t 3 /nobreak >nul
echo [OK] Public API server starting...
echo [INFO] Wait a few seconds for it to fully start before testing.

echo.
echo [3/4] Verifying chat channel...
python -c "from ae import repo; channels = repo.list_chat_channels('acq.db'); client_channels = [ch for ch in channels if ch.meta_json.get('client_id') == 'test-massage-spa']; print('[OK] Chat channel:', client_channels[0].provider.value if client_channels else 'NOT FOUND')" 2>nul
if errorlevel 1 (
    echo [WARNING] Chat channel may not be configured
)

echo.
echo [4/4] Checking landing page...
if exist "exports\static_site\demo-service-page\index.html" (
    echo [OK] Landing page exists: exports\static_site\demo-service-page\index.html
) else (
    echo [WARNING] Landing page not found. You may need to publish it first.
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Wait a few seconds for API server to fully start
echo 2. Open landing page: exports\static_site\demo-service-page\index.html
echo 3. Or serve it: cd exports\static_site\demo-service-page ^&^& python -m http.server 8080
echo 4. Click a package to test the flow
echo 5. Check results: python check_package_events.py
echo.
echo To stop the API server, close its window or press Ctrl+C in that window.
echo.
pause
