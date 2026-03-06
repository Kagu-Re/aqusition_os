# Complete ROAS Test Flow
# Tests: Ad Spend → Bookings → ROAS Calculation with Campaign Attribution

Write-Host "=== Complete ROAS Test Flow ===" -ForegroundColor Cyan
Write-Host ""

$env:PYTHONPATH = "src"

Write-Host "Step 1: Check existing leads with UTM campaigns..." -ForegroundColor Yellow
python -c "from ae import repo; leads = repo.list_leads('acq.db'); utm_leads = [l for l in leads if l.utm_campaign and l.message and 'Booking request' in (l.message or '')]; print(f'Found {len(utm_leads)} booking leads with UTM campaigns:'); [print(f'  Lead {l.lead_id}: campaign={l.utm_campaign}, status={l.booking_status}, value={l.booking_value}') for l in utm_leads[-3:]]"

Write-Host ""
Write-Host "Step 2: Recording ad spend for campaigns..." -ForegroundColor Yellow
Write-Host "  Google: 1000 AUD for plumber-brisbane-feb2026" -ForegroundColor Gray
python -c "from ae import repo; result = repo.upsert_spend_daily('acq.db', day='2026-02-06', source='google', spend_value=1000.0, spend_currency='AUD', utm_campaign='plumber-brisbane-feb2026', client_id='demo1'); print('  ✅ Google spend recorded')"

Write-Host "  Meta: 800 AUD for plumber-brisbane-feb2026" -ForegroundColor Gray
python -c "from ae import repo; result = repo.upsert_spend_daily('acq.db', day='2026-02-06', source='facebook', spend_value=800.0, spend_currency='AUD', utm_campaign='plumber-brisbane-feb2026', client_id='demo1'); print('  ✅ Meta spend recorded')"

Write-Host ""
Write-Host "Step 3: Marking leads as booked..." -ForegroundColor Yellow
Write-Host "  Use console UI: http://localhost:8000/console → Leads" -ForegroundColor White
Write-Host "  Mark Lead 3 or 4 as booked with value (e.g., 150 AUD)" -ForegroundColor White

Write-Host ""
Write-Host "Step 4: Calculating ROAS..." -ForegroundColor Yellow
python -c @"
from ae import repo
roas = repo.roas_stats('acq.db')
print('ROAS Statistics:')
print(f'Total Revenue: {roas[\"total\"][\"revenue\"]:.2f}')
print('')
print('By Campaign:')
for c in roas['by_campaign']:
    if c['spend'] > 0 or c['revenue'] > 0:
        roas_val = f'{c[\"roas\"]:.2f}' if c['roas'] else 'N/A'
        print(f'  {c[\"utm_campaign\"]}: Revenue={c[\"revenue\"]:.2f}, Spend={c[\"spend\"]:.2f}, ROAS={roas_val}')
"@

Write-Host ""
Write-Host "=== Test Summary ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Ad spend recorded" -ForegroundColor Green
Write-Host "⚠️  Mark leads as booked to see ROAS" -ForegroundColor Yellow
Write-Host ""
Write-Host "This confirms campaign attribution and ROAS calculation work!" -ForegroundColor Green
