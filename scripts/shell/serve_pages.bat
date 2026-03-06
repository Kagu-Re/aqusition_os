@echo off
REM Serve static pages for inspection
REM Usage: serve_pages.bat [port]

set PORT=%1
if "%PORT%"=="" set PORT=8080

echo ========================================
echo Serving Landing Pages for Inspection
echo ========================================
echo.
echo Port: %PORT%
echo.
echo Pages will be available at:
echo   http://localhost:%PORT%/[page-id]/index.html
echo.
echo Available pages:
echo   - test-massage-spa-main
echo   - test-massage-spa-premium
echo   - test-massage-spa-express
echo   - demo-service-page
echo   - test-service-page
echo.
echo Press Ctrl+C to stop the server
echo.
echo ========================================
echo.

cd exports\static_site
python -m http.server %PORT%
