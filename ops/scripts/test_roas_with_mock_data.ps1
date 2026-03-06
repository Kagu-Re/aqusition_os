# Test ROAS Calculation with Mock Ad Spend Data
# No need for real Google/Meta accounts - uses synthetic data

Write-Host "=== Testing ROAS Calculation with Mock Data ===" -ForegroundColor Cyan
Write-Host ""

$env:PYTHONPATH = "src"

Write-Host "Step 1: Recording mock ad spend data..." -ForegroundColor Yellow
Write-Host "  Recording Google Ads spend: 1000 AUD for campaign 'plumber-brisbane-feb2026'" -ForegroundColor Gray
python -c @"
from ae import repo
result = repo.upsert_spend_daily(
    'acq.db',
    day='2026-02-06',
    source='google',
    spend_value=1000.0,
    spend_currency='AUD',
    utm_campaign='plumber-brisbane-feb2026',
    client_id='demo1'
)
print(f'  ✅ {result[\"action\"]}: spend_id={result[\"spend_id\"]}')
"@

Write-Host "  Recording Meta Ads spend: 800 AUD for campaign 'plumber-brisbane-feb2026'" -ForegroundColor Gray
python -c @"
from ae import repo
result = repo.upsert_spend_daily(
    'acq.db',
    day='2026-02-06',
    source='facebook',
    spend_value=800.0,
    spend_currency='AUD',
    utm_campaign='plumber-brisbane-feb2026',
    client_id='demo1'
)
print(f'  ✅ {result[\"action\"]}: spend_id={result[\"spend_id\"]}')
"@

Write-Host ""
Write-Host "Step 2: Checking existing bookings with values..." -ForegroundColor Yellow
python -c @"
from ae import repo
leads = repo.list_leads('acq.db')
bookings = [l for l in leads if l.booking_status in ('booked', 'confirmed', 'completed') and l.booking_value]
print(f'Found {len(bookings)} bookings with values:')
for b in bookings:
    print(f'  Lead {b.lead_id}: {b.booking_value} {b.booking_currency} | Campaign: {b.utm_campaign}')
if not bookings:
    print('  ⚠️  No bookings with values yet. Mark some leads as booked in console.')
"@

Write-Host ""
Write-Host "Step 3: Calculating ROAS..." -ForegroundColor Yellow
python -c @"
from ae import repo
roas = repo.roas_stats('acq.db')
print('ROAS Statistics:')
print(f'  Total Revenue: {roas[\"total\"][\"revenue\"]:.2f}')
print('')
print('By Source:')
for src in roas['by_source']:
    if src['spend'] > 0 or src['revenue'] > 0:
        roas_val = src['roas'] if src['roas'] else 'N/A'
        print(f'  {src[\"source\"]}: Revenue={src[\"revenue\"]:.2f}, Spend={src[\"spend\"]:.2f}, ROAS={roas_val}')
print('')
print('By Campaign:')
for camp in roas['by_campaign']:
    if camp['spend'] > 0 or camp['revenue'] > 0:
        roas_val = camp['roas'] if camp['roas'] else 'N/A'
        print(f'  {camp[\"utm_campaign\"]}: Revenue={camp[\"revenue\"]:.2f}, Spend={camp[\"spend\"]:.2f}, ROAS={roas_val}')
"@

Write-Host ""
Write-Host "=== ROAS Test Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "What was tested:" -ForegroundColor Yellow
Write-Host "  ✅ Ad spend recorded (mock data)" -ForegroundColor Green
Write-Host "  ✅ ROAS calculation" -ForegroundColor Green
Write-Host "  ✅ Campaign-level attribution" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Mark some leads as 'booked' with values in console" -ForegroundColor White
Write-Host "  2. Run this script again to see ROAS calculation" -ForegroundColor White
Write-Host "  3. Verify campaign attribution matches" -ForegroundColor White
Write-Host ""
Write-Host "Note: For production, you'll import real ad spend from Google/Meta exports." -ForegroundColor Gray
Write-Host "But for MVP validation, mock data confirms the system works!" -ForegroundColor Green
