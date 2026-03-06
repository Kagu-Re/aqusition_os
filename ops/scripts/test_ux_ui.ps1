# UX/UI Testing Script for Console
# Tests accessibility, form validation, and UI improvements

param(
    [string]$ConsoleUrl = "http://localhost:8000/console",
    [int]$Timeout = 10
)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Console UX/UI Testing" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$results = @{
    "Server Running" = $false
    "Console Page Loads" = $false
    "Skip Link Present" = $false
    "Mobile Menu Present" = $false
    "ARIA Attributes" = $false
    "CSS Loading" = $false
    "Form Elements" = $false
}

# Test 1: Check if server is running
Write-Host "[1/7] Checking if console server is running..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$ConsoleUrl" -TimeoutSec $Timeout -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "  ✅ Console server is running" -ForegroundColor Green
        $results["Server Running"] = $true
    }
} catch {
    Write-Host "  ❌ Console server is NOT running" -ForegroundColor Red
    Write-Host "  Start it with: python -m ae.console_app" -ForegroundColor Yellow
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 2: Check if console page loads
Write-Host ""
Write-Host "[2/7] Checking if console page loads correctly..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$ConsoleUrl" -TimeoutSec $Timeout -ErrorAction Stop
    $html = $response.Content
    
    if ($html -match "page-container" -and $html -match "Operator Console") {
        Write-Host "  ✅ Console page loads correctly" -ForegroundColor Green
        $results["Console Page Loads"] = $true
    } else {
        Write-Host "  ⚠️  Page loads but may be missing elements" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ❌ Failed to load console page" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Check for skip link
Write-Host ""
Write-Host "[3/7] Checking for skip link (accessibility)..." -ForegroundColor Yellow
if ($html -match 'skip-link' -or $html -match 'Skip to main content') {
    Write-Host "  ✅ Skip link is present" -ForegroundColor Green
    $results["Skip Link Present"] = $true
} else {
    Write-Host "  ❌ Skip link is missing" -ForegroundColor Red
}

# Test 4: Check for mobile menu
Write-Host ""
Write-Host "[4/7] Checking for mobile menu toggle..." -ForegroundColor Yellow
if ($html -match 'mobile-menu-toggle' -or $html -match 'aria-expanded') {
    Write-Host "  ✅ Mobile menu toggle is present" -ForegroundColor Green
    $results["Mobile Menu Present"] = $true
} else {
    Write-Host "  ❌ Mobile menu toggle is missing" -ForegroundColor Red
}

# Test 5: Check for ARIA attributes
Write-Host ""
Write-Host "[5/7] Checking for ARIA attributes..." -ForegroundColor Yellow
$ariaChecks = @(
    'aria-label',
    'aria-required',
    'aria-invalid',
    'aria-describedby',
    'aria-live',
    'aria-busy',
    'role="navigation"',
    'role="main"'
)

$ariaFound = 0
foreach ($attr in $ariaChecks) {
    if ($html -match $attr) {
        $ariaFound++
    }
}

if ($ariaFound -ge 4) {
    Write-Host "  ✅ ARIA attributes are present ($ariaFound found)" -ForegroundColor Green
    $results["ARIA Attributes"] = $true
} else {
    Write-Host "  ⚠️  Some ARIA attributes may be missing ($ariaFound found)" -ForegroundColor Yellow
}

# Test 6: Check CSS loading
Write-Host ""
Write-Host "[6/7] Checking if CSS files are referenced..." -ForegroundColor Yellow
if ($html -match 'styles\.css' -or $html -match 'tailwind\.css') {
    Write-Host "  ✅ CSS files are referenced" -ForegroundColor Green
    $results["CSS Loading"] = $true
} else {
    Write-Host "  ⚠️  CSS files may not be loading" -ForegroundColor Yellow
}

# Test 7: Check for form elements with proper attributes
Write-Host ""
Write-Host "[7/7] Checking form elements..." -ForegroundColor Yellow
$formChecks = @(
    'form-field',
    'aria-required',
    'error-message',
    'required-indicator'
)

$formFound = 0
foreach ($check in $formChecks) {
    if ($html -match $check) {
        $formFound++
    }
}

if ($formFound -ge 2) {
    Write-Host "  ✅ Form elements have proper structure ($formFound found)" -ForegroundColor Green
    $results["Form Elements"] = $true
} else {
    Write-Host "  ⚠️  Form elements may need improvements ($formFound found)" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$passed = 0
$total = $results.Count

foreach ($test in $results.GetEnumerator() | Sort-Object Name) {
    $status = if ($test.Value) { "✅ PASS" } else { "❌ FAIL" }
    $color = if ($test.Value) { "Green" } else { "Red" }
    Write-Host "  $status : $($test.Key)" -ForegroundColor $color
    if ($test.Value) { $passed++ }
}

Write-Host ""
Write-Host "Results: $passed/$total tests passed" -ForegroundColor $(if ($passed -eq $total) { "Green" } else { "Yellow" })
Write-Host ""

if ($passed -eq $total) {
    Write-Host "✅ All automated tests passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Open $ConsoleUrl in your browser" -ForegroundColor White
    Write-Host "  2. Test keyboard navigation (Tab key)" -ForegroundColor White
    Write-Host "  3. Test form validation on Landing Pages form" -ForegroundColor White
    Write-Host "  4. Test mobile menu (resize browser < 1024px)" -ForegroundColor White
    Write-Host "  5. Check browser console for errors (F12)" -ForegroundColor White
    exit 0
} else {
    Write-Host "⚠️  Some tests failed. Please check the console manually." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Manual testing:" -ForegroundColor Cyan
    Write-Host "  1. Open $ConsoleUrl in your browser" -ForegroundColor White
    Write-Host "  2. Check browser console (F12) for errors" -ForegroundColor White
    Write-Host "  3. Verify elements are present" -ForegroundColor White
    exit 1
}
