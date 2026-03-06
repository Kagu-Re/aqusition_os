# Quote to Chat Flow

This document explains how the "Get a quote" button redirects users to chat for further interactions.

## Overview

When a user clicks the "Get a quote" button on a landing page:
1. The `quote_submit` event is tracked
2. The page fetches the client's chat channel information
3. The user is redirected to the appropriate chat platform (WhatsApp, LINE, phone, etc.)

## Architecture

### Components

1. **Public API Endpoint** (`/v1/chat/channel`)
   - Returns chat channel information for a client
   - Generates appropriate chat URLs based on provider type

2. **HTML Tracking JavaScript**
   - Fetches chat channel info on page load
   - Handles quote button clicks
   - Redirects to chat after tracking the event

3. **Chat Channel Registry**
   - Stores chat channel configurations in the database
   - Links channels to clients via `meta_json.client_id`

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

The published HTML will automatically include chat redirect functionality.

## How It Works

### Page Load

When the page loads, JavaScript automatically:

1. Fetches chat channel info from `/v1/chat/channel?client_id=CLIENT_ID&db=acq.db`
2. Stores the `chat_url` for later use
3. If no chat channel is found, the quote button will still track events but won't redirect

### Quote Button Click

When a user clicks "Get a quote":

1. **Event Tracking**: The `quote_submit` event is sent to `/v1/event`
2. **Chat Redirect**: If a chat URL is available, the user is redirected after a 100ms delay (to ensure the event is sent)

### Fallback Behavior

If no chat channel is registered:
- The `quote_submit` event is still tracked
- The button behaves normally (no redirect)
- The system falls back to the client's `primary_phone` if available (for phone/SMS)

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
3. Click "Get a quote" button
4. Verify:
   - Event is sent to `/v1/event` with `event_name: "quote_submit"`
   - Page redirects to the chat URL (e.g., WhatsApp)

## Troubleshooting

### "No chat channel found"

**Cause**: No chat channel registered for the client.

**Solution**: Register a chat channel with `meta_json.client_id` matching your client ID.

### "Chat redirect not working"

**Possible causes**:
1. Chat channel API not accessible (check CORS settings)
2. Client ID mismatch
3. JavaScript errors in browser console

**Solution**:
1. Check browser console for errors
2. Verify API endpoint is accessible: `curl "http://localhost:8001/v1/chat/channel?client_id=CLIENT_ID&db=acq.db"`
3. Check that `AE_PUBLIC_API_URL` matches your public API server URL

### "Event tracked but no redirect"

**Cause**: Chat channel fetch failed or returned no URL.

**Solution**:
1. Check Network tab for failed requests to `/v1/chat/channel`
2. Verify chat channel is registered correctly
3. Check browser console for JavaScript errors

## API Reference

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

## Next Steps

After setting up quote-to-chat flow:

1. ✅ Test quote submission tracking
2. ✅ Verify chat redirect works
3. ✅ Monitor chat conversations in console
4. ✅ Link conversations to leads (via `lead_id` in conversation metadata)
5. ✅ Set up chat automation templates for automated responses
