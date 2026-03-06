@echo off
REM Start Public API Server for Landing Pages
REM This server provides the /v1/service-packages endpoint needed for package display

echo ========================================
echo Starting Public API Server
echo ========================================
echo.
echo This server provides:
echo   - /v1/service-packages (for package display)
echo   - /v1/event (for event tracking)
echo   - /lead (for lead intake)
echo   - /v1/chat/channel (for chat redirect)
echo.
echo Server will run on: http://localhost:8001
echo.
echo Keep this window open while viewing landing pages.
echo Press Ctrl+C to stop the server.
echo.
echo ========================================
echo.

set PYTHONPATH=src
python -m ae.cli run-public --host 127.0.0.1 --port 8001
