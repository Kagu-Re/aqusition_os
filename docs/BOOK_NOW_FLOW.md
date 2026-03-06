# Book Now Flow

This document explains how the "Book now" button works, including event tracking, lead creation, and chat/phone redirect.

## Overview

When a user clicks the "Book now" button on a landing page:
1. The `call_click` event is tracked (for attribution)
2. A lead is automatically created with booking intent
3. The user is redirected to the appropriate chat platform or phone (WhatsApp, LINE, Telegram, phone, etc.)
4. Operator manually creates booking from the lead in the console

## Architecture

### Components

1. **Public API Endpoint** (`/v1/lead`)
   - Creates a lead record with booking intent
   - Stores attribution data (UTM parameters)
   - Links lead to client and page

2. **Public API Endpoint** (`/v1/chat/channel`)
   - Returns chat channel information for a client
   - Generates appropriate chat URLs based on provider type

3. **HTML Tracking JavaScript**
   - Fetches chat channel info on page load
   - Handles "Book now" button clicks
   - Creates lead automatically
   - Redirects to chat/phone after tracking

4. **Console UI**
   - Operator views new leads
   - Operator creates booking from lead
   - Operator tracks payment

## Setup

### Step 1: Register a Chat Channel

Register a chat channel for your client via the console API:

```bash
curl -X POST http://localhost:8000/api/chat/channels?db=acq.db \
  -H "Content-Type: application/json" \
  -H "X-AE-SECRET: YOUR_SECRET" \
  -d '{
    "channel_id": "ch_demo1_whatsapp",
    "provider": "whatsapp",
    "handle": "+61-400-000-000",
    "display_name": "Demo Plumbing WhatsApp",
    "meta_json": {"client_id": "demo1"}
  }'
```

Or via Python:

```python
from ae import repo
from ae.enums import ChatProvider

repo.upsert_chat_channel(
    db_path="acq.db",
    channel_id="ch_demo1_whatsapp",
    provider=ChatProvider.whatsapp,
    handle="+61-400-000-000",
    display_name="Demo Plumbing WhatsApp",
    meta_json={"client_id": "demo1"}
)
```

### Step 2: Supported Chat Providers

The system supports the following chat providers:

| Provider | Handle Format | Generated URL |
|----------|--------------|---------------|
| **WhatsApp** | Phone number (e.g., `+61-400-000-000`) | `https://wa.me/61400000000` |
| **LINE** | LINE ID (e.g., `@line_id` or `U1234567890`) | `https://line.me/R/ti/p/@line_id` |
| **SMS/Phone** | Phone number | `tel:+61400000000` |
| **Telegram** | Username (e.g., `@username`) | `https://t.me/username` |
| **Messenger** | Page username | `https://m.me/username` |

### Step 3: Publish Page

After registering the chat channel, publish your page:

```bash
python -m ae.cli publish-page --db acq.db --page-id p-demo1-v1
```

The published HTML will automatically include "Book now" functionality.

## How It Works

### Page Load

When the page loads, JavaScript automatically:

1. Fetches chat channel info from `/v1/chat/channel?client_id=CLIENT_ID&db=acq.db`
2. Stores the `chat_url` for later use
3. If no chat channel is found, the "Book now" button will still track events and create leads but won't redirect

### Book Now Button Click

When a user clicks "Book now":

1. **Event Tracking**: The `call_click` event is sent to `/v1/event` (for attribution tracking)
2. **Lead Creation**: A lead is automatically created via `POST /v1/lead` with:
   - `source`: "landing_page"
   - `page_id`: Current page ID
   - `client_id`: Client ID
   - `message`: "Booking request from landing page"
   - `utm`: UTM parameters from URL
   - `status`: "new" (default)
   - `booking_status`: "none" (default, operator will update)
3. **Chat Redirect**: If a chat URL is available, the user is redirected after a 200ms delay (to ensure the lead is created)

### Fallback Behavior

If no chat channel is registered:
- The `call_click` event is still tracked
- The lead is still created
- The button behaves normally (no redirect)
- The system falls back to the client's `primary_phone` if available (for phone/SMS)

## Operator Workflow

### Step 1: View New Leads

Open the console at `/console` → Leads section.

New leads from "Book now" clicks will appear with:
- `status`: "new"
- `message`: "Booking request from landing page"
- `booking_status`: "none"
- UTM attribution data (utm_source, utm_campaign, etc.)

### Step 2: Contact Customer

Contact the customer via:
- Phone (if phone number available)
- Chat (WhatsApp, LINE, Telegram)
- Email (if email available)

### Step 3: Collect Booking Details

During the conversation, collect:
- Service needed
- Date/time
- Address (if applicable)
- Price/quote

### Step 4: Create Booking

In the console, update the lead:

```javascript
// In console UI
updateLeadOutcome(leadId, {
  booking_status: "booked",
  booking_value: 150.00,
  booking_currency: "AUD",
  status: "qualified"
});
```

Or via API:

```bash
curl -X POST http://localhost:8000/api/leads/{lead_id}/outcome?db=acq.db \
  -H "Content-Type: application/json" \
  -H "X-AE-SECRET: YOUR_SECRET" \
  -d '{
    "booking_status": "booked",
    "booking_value": 150.00,
    "booking_currency": "AUD",
    "status": "qualified"
  }'
```

### Step 5: Track Payment (Optional)

If payment is received, create a payment record:

```bash
curl -X POST http://localhost:8000/api/payments?db=acq.db \
  -H "Content-Type: application/json" \
  -H "X-AE-SECRET: YOUR_SECRET" \
  -d '{
    "payment_id": "pay_123",
    "booking_id": "lead-{lead_id}",
    "lead_id": {lead_id},
    "amount": 150.00,
    "currency": "AUD",
    "provider": "manual",
    "method": "cash",
    "status": "captured"
  }'
```

Then update booking status:

```javascript
updateLeadOutcome(leadId, {
  booking_status: "confirmed"
});
```

## Testing

### 1. Register a Chat Channel

```bash
# Register WhatsApp channel
curl -X POST http://localhost:8000/api/chat/channels?db=acq.db \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "ch_test_whatsapp",
    "provider": "whatsapp",
    "handle": "+66-80-123-4567",
    "display_name": "Test WhatsApp",
    "meta_json": {"client_id": "YOUR_CLIENT_ID"}
  }'
```

### 2. Verify Channel API

```bash
# Test the public API endpoint
curl "http://localhost:8001/v1/chat/channel?client_id=YOUR_CLIENT_ID&db=acq.db"
```

Expected response:
```json
{
  "channel_id": "ch_test_whatsapp",
  "provider": "whatsapp",
  "handle": "+66-80-123-4567",
  "display_name": "Test WhatsApp",
  "chat_url": "https://wa.me/66801234567"
}
```

### 3. Test on Published Page

1. Open the published HTML page in a browser
2. Open browser DevTools → Network tab
3. Click "Book now" button
4. Verify:
   - Event is sent to `/v1/event` with `event_name: "call_click"`
   - Lead is created via `POST /v1/lead`
   - Page redirects to the chat URL (e.g., WhatsApp)

### 4. Verify Lead Creation

Check the console or query the database:

```bash
# View leads via console
# Open: http://localhost:8000/console → Leads

# Or query database
python -c "
from ae import repo
leads = repo.list_leads('acq.db', limit=10)
for lead in leads:
    if 'Booking request' in (lead.message or ''):
        print(f'Lead {lead.lead_id}: {lead.message}')
"
```

## Comparison: "Get a Quote" vs "Book Now"

| Feature | "Get a quote" | "Book now" |
|---------|---------------|------------|
| **Event** | `quote_submit` | `call_click` |
| **Lead Created** | No (manual) | Yes (automatic) |
| **Redirect** | Chat | Phone/Chat |
| **Purpose** | Initial inquiry | Booking intent |
| **Operator Action** | Contact for quote | Create booking |

**Key Difference**: "Book now" creates a lead immediately, making it easier for operators to track and convert to bookings.

## Troubleshooting

### "No chat channel found"

**Cause**: No chat channel registered for the client.

**Solution**: Register a chat channel with `meta_json.client_id` matching your client ID.

### "Lead not created"

**Possible causes**:
1. API endpoint not accessible (check CORS settings)
2. JavaScript errors in browser console
3. Network request failed

**Solution**:
1. Check browser console for errors
2. Verify API endpoint is accessible: `curl "http://localhost:8001/v1/lead?db=acq.db"`
3. Check Network tab for failed requests to `/v1/lead`
4. Verify `AE_PUBLIC_API_URL` matches your public API server URL

### "Event tracked but no redirect"

**Cause**: Chat channel fetch failed or returned no URL.

**Solution**:
1. Check Network tab for failed requests to `/v1/chat/channel`
2. Verify chat channel is registered correctly
3. Check browser console for JavaScript errors

### "Lead created but booking status not updating"

**Cause**: Operator hasn't updated the lead yet, or API call failed.

**Solution**:
1. Check console UI for the lead
2. Verify operator has permissions to update leads
3. Check browser console for JavaScript errors when clicking "✓ booked"

## API Reference

### POST `/v1/lead`

Create a lead from a landing page form or button click.

**Query Parameters**:
- `db` (optional): Database path (default: `acq.db`)

**Request Body**:
```json
{
  "source": "landing_page",
  "page_id": "p-demo1-v1",
  "client_id": "demo1",
  "message": "Booking request from landing page",
  "utm": {
    "utm_source": "google",
    "utm_medium": "paid",
    "utm_campaign": "demo-campaign"
  }
}
```

**Response**:
```json
{
  "lead_id": 123,
  "status": "new",
  "booking_status": "none"
}
```

### GET `/v1/chat/channel`

Get chat channel information for a client.

**Query Parameters**:
- `client_id` (required): Client ID
- `provider` (optional): Filter by provider (e.g., `whatsapp`, `line`)
- `db` (optional): Database path (default: `acq.db`)

**Response**:
```json
{
  "channel_id": "ch_demo1_whatsapp",
  "provider": "whatsapp",
  "handle": "+61-400-000-000",
  "display_name": "Demo Plumbing WhatsApp",
  "chat_url": "https://wa.me/61400000000"
}
```

**Error Response** (404):
```json
{
  "detail": "No chat channel found for client: demo1"
}
```

## Data Flow

### 1. Event Tracking
```
Browser → POST /v1/event → events table
```
- `event_name`: "call_click"
- Attribution data (UTM params)

### 2. Lead Creation
```
Browser → POST /v1/lead → lead_intake table
```
- `source`: "landing_page"
- `message`: "Booking request from landing page"
- `status`: "new"
- `booking_status`: "none"
- Attribution data (UTM params)

### 3. Booking Creation (Manual)
```
Operator → Console UI → updateLeadOutcome() → lead_intake table
```
- `booking_status`: "none" → "booked"
- `booking_value`: Set by operator
- `booking_currency`: Set by operator
- `status`: "new" → "qualified"

### 4. Payment Tracking (Manual)
```
Operator → Console UI → createPayment() → payments table
```
- `payment_id`: Generated
- `booking_id`: "lead-{lead_id}"
- `amount`, `currency`: From booking
- `status`: "pending" → "captured"

## Why This Design?

### ✅ Aligns with GTM Strategy

1. **Service Businesses Handle Bookings Manually**
   - They use phone/WhatsApp anyway
   - No need for automated chatbot (not ready)
   - Operator creates booking after talking to customer

2. **Attribution Tracking is Key**
   - Track which ad led to booking intent
   - ROAS calculation works
   - Campaign optimization possible

3. **Simple & Reliable**
   - No complex chatbot logic
   - No payment gateway integration needed
   - Works with existing infrastructure

4. **Operator-Friendly**
   - Leads appear in console immediately
   - Clear booking intent (message field)
   - Easy to convert to booking

## Next Steps

After setting up "Book now" flow:

1. ✅ Test "Book now" button tracking
2. ✅ Verify lead creation works
3. ✅ Test chat/phone redirect
4. ✅ Monitor leads in console
5. ✅ Create bookings from leads
6. ✅ Track payments (if applicable)
7. ✅ Analyze ROAS by campaign

## Future Enhancements (Not MVP)

### Phase 2: Automated Booking Flow
- Chatbot collects booking details
- Automated booking creation
- Calendar integration

### Phase 3: Payment Gateway Integration
- Payment link generation
- Automated payment processing
- Webhook handling

**For Now**: Keep it simple and manual, aligned with GTM strategy.
