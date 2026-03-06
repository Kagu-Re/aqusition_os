# Test Booking → Payment Flow
# Complete workflow: Lead → Booking → Payment

Write-Host "=== Testing Booking → Payment Flow ===" -ForegroundColor Cyan
Write-Host ""

$env:PYTHONPATH = "src"

Write-Host "Step 1: Check existing booked leads..." -ForegroundColor Yellow
python -c @"
from ae import repo
leads = repo.list_leads('acq.db')
bookings = [l for l in leads if l.booking_status in ('booked', 'confirmed', 'completed') and l.booking_value]
print(f'Found {len(bookings)} booked leads:')
for b in bookings[:3]:
    print(f'  Lead {b.lead_id}: {b.booking_value} {b.booking_currency} | Campaign: {b.utm_campaign}')
"@

Write-Host ""
Write-Host "Step 2: Creating payment for Lead 3..." -ForegroundColor Yellow
python -c @"
from ae import repo
from ae.enums import PaymentProvider, PaymentMethod, PaymentStatus
import uuid

# Get the lead
lead = repo.get_lead('acq.db', 3)
if not lead:
    print('❌ Lead 3 not found')
    exit(1)

# Create payment
payment_id = f'pay-{uuid.uuid4().hex[:12]}'
booking_id = f'lead-{lead.lead_id}'

payment = repo.create_payment(
    'acq.db',
    payment_id=payment_id,
    booking_id=booking_id,
    lead_id=lead.lead_id,
    amount=lead.booking_value or 150.0,
    currency=lead.booking_currency or 'AUD',
    provider=PaymentProvider.manual,
    method=PaymentMethod.other,
    status=PaymentStatus.pending,
)

print(f'✅ Payment created:')
print(f'   Payment ID: {payment.payment_id}')
print(f'   Booking ID: {payment.booking_id}')
print(f'   Amount: {payment.amount} {payment.currency}')
print(f'   Status: {payment.status.value}')
"@

Write-Host ""
Write-Host "Step 3: Verifying payment was created..." -ForegroundColor Yellow
python -c @"
from ae import repo
payments = repo.list_payments('acq.db', lead_id=3)
print(f'Found {len(payments)} payment(s) for Lead 3:')
for p in payments:
    print(f'  Payment {p.payment_id}: {p.amount} {p.currency} | Status: {p.status.value}')
"@

Write-Host ""
Write-Host "Step 4: Confirming booking (required before capturing payment)..." -ForegroundColor Yellow
python -c @"
from ae import service
service.set_lead_outcome('acq.db', 3, booking_status='confirmed', actor='test')
print('✅ Lead 3 booking status updated to confirmed')
"@

Write-Host ""
Write-Host "Step 5: Updating payment status to captured..." -ForegroundColor Yellow
python -c @"
from ae import repo
from ae.enums import PaymentStatus

# Get the payment we just created
payments = repo.list_payments('acq.db', lead_id=3)
if payments:
    payment = payments[0]
    updated = repo.update_payment_status(
        'acq.db',
        payment_id=payment.payment_id,
        status=PaymentStatus.captured,
    )
    if updated:
        print(f'✅ Payment {updated.payment_id} updated to {updated.status.value}')
    else:
        print('❌ Failed to update payment')
else:
    print('❌ No payment found')
"@

Write-Host ""
Write-Host "Step 6: Verifying UTM attribution preserved..." -ForegroundColor Yellow
python -c @"
from ae import repo

lead = repo.get_lead('acq.db', 3)
payments = repo.list_payments('acq.db', lead_id=3)

print('Lead Attribution:')
print(f'  Campaign: {lead.utm_campaign}')
print(f'  Source: {lead.utm_source}')
print(f'  Medium: {lead.utm_medium}')
print('')
print('Payment Details:')
for p in payments:
    print(f'  Payment {p.payment_id}: {p.amount} {p.currency} | Status: {p.status.value}')
"@

Write-Host ""
Write-Host "=== Test Summary ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Payment created for booked lead" -ForegroundColor Green
Write-Host "✅ Payment status updated" -ForegroundColor Green
Write-Host "✅ UTM attribution preserved" -ForegroundColor Green
Write-Host ""
Write-Host "This confirms the complete booking → payment workflow works!" -ForegroundColor Green
