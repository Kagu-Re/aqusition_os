# Verify UTM Attribution in Events and Leads
# Run this after testing "Book now" with UTM parameters

Write-Host "=== Verifying UTM Attribution ===" -ForegroundColor Cyan
Write-Host ""

$env:PYTHONPATH = "src"

# Check events
Write-Host "Recent Events:" -ForegroundColor Yellow
python -c @"
import sqlite3
import json
conn = sqlite3.connect('acq.db')
cur = conn.execute('SELECT event_name, timestamp, params_json FROM events ORDER BY timestamp DESC LIMIT 3')
events = cur.fetchall()
for e in events:
    print(f'  {e[0]} at {e[1]}')
    params = json.loads(e[2])
    utm_source = params.get('utm_source', 'None')
    utm_campaign = params.get('utm_campaign', 'None')
    print(f'    UTM: source={utm_source}, campaign={utm_campaign}')
conn.close()
"@

Write-Host ""
Write-Host "Recent Booking Leads:" -ForegroundColor Yellow
python -c @"
from ae import repo
leads = repo.list_leads('acq.db')
booking_leads = [l for l in leads if l.message and 'Booking request' in (l.message or '')]
if booking_leads:
    for lead in booking_leads[-3:]:
        print(f'  Lead {lead.lead_id} ({lead.ts}):')
        print(f'    utm_source: {lead.utm_source}')
        print(f'    utm_medium: {lead.utm_medium}')
        print(f'    utm_campaign: {lead.utm_campaign}')
        print(f'    utm_term: {lead.utm_term}')
        print(f'    utm_content: {lead.utm_content}')
        print('')
else:
    print('  No booking leads found')
"@

Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "If UTM params show 'None', the test URL didn't include UTM parameters." -ForegroundColor Yellow
Write-Host "Test with: http://localhost:8080/p1/index.html?utm_source=google&utm_medium=cpc&utm_campaign=test" -ForegroundColor White
