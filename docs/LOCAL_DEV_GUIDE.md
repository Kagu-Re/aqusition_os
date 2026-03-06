# Local Development Guide - All-in-One Server

## Overview

Run everything locally without ngrok! The unified server includes:
- ✅ **Console** (Money Board, etc.) at `/console`
- ✅ **Public API** at `/api` and `/v1/*`
- ✅ **Landing Pages** at `/pages/{page_id}`
- ✅ **Telegram Bots** (polling mode - no webhook needed)

## Quick Start

### Step 1: Start the Server

```powershell
.\start_local_dev.ps1
```

Or manually:
```powershell
$env:PYTHONPATH = "src"
python -m uvicorn ae.local_dev_server:app --host 127.0.0.1 --port 8000 --reload
```

### Step 2: Access Services

Once started, you'll see:
```
Services available:
  📊 Console:        http://localhost:8000/console
  💰 Money Board:    http://localhost:8000/money-board
  🌐 Public API:     http://localhost:8000/api
  📄 Landing Pages:  http://localhost:8000/pages/{page_id}
  🤖 Telegram Bots:  Polling mode (no webhook needed)
```

### Step 3: Test Telegram Bot

1. **Send a message** to `@massage_thaibot` on Telegram
2. **Check server logs** - you should see the message received
3. **Check database** - message should be stored

**No webhook setup needed!** The bot uses polling mode for local development.

## What's Different from Webhook Mode?

### Webhook Mode (Production)
- Telegram sends updates to your server
- Requires public HTTPS endpoint (ngrok in dev)
- More efficient for production

### Polling Mode (Local Dev)
- Server polls Telegram API for updates
- No public endpoint needed
- Perfect for local development
- Automatically enabled in local dev server

## Services Breakdown

### 1. Console (`/console`)
- Operator console interface
- Client management
- Page management
- All admin features

### 2. Money Board (`/money-board`)
- Booking management interface
- View bookings by status
- Update booking status
- Send messages to customers

### 3. Public API (`/api`, `/v1/*`)
- Lead intake: `POST /lead`
- Service packages: `GET /v1/service-packages`
- Chat channels: `GET /v1/chat/channel`
- Events: `POST /v1/event`
- QR codes: `GET /v1/qr/generate`

### 4. Landing Pages (`/pages/{page_id}`)
- Serves published landing pages
- Includes packages display
- Deep link support for Telegram
- Example: `http://localhost:8000/pages/p1`

### 5. Telegram Bots (Background)
- **Customer Bot**: Receives messages, handles deep links
- **Vendor Bot**: (Future) Manages bookings via Telegram
- Both run in polling mode automatically

## Testing the Full Flow

### 1. Landing Page → Telegram Bot

1. **Publish a landing page:**
   ```bash
   python -m ae.cli publish-page --db acq.db --page-id p1
   ```

2. **Visit landing page:**
   ```
   http://localhost:8000/pages/p1
   ```

3. **Click on a package:**
   - Should redirect to Telegram bot
   - Deep link: `t.me/massage_thaibot?start=package_pkg123`

4. **Bot receives message:**
   - Check server logs
   - Bot confirms package selection

### 2. Money Board → Telegram

1. **Open Money Board:**
   ```
   http://localhost:8000/money-board
   ```

2. **Send package menu:**
   - Click "Send Package Menu" on a lead
   - Message sent via Telegram (polling mode)

3. **Customer receives message:**
   - Check Telegram bot
   - Customer can respond

### 3. Telegram → Money Board

1. **Customer sends message:**
   - Message received via polling
   - Stored in database
   - Event emitted

2. **View in Money Board:**
   - Conversation appears
   - Messages visible
   - Can respond via Money Board UI

## Configuration

### Environment Variables

```powershell
# Database path (default: acq.db)
$env:AE_DB_PATH = "acq.db"

# Public API URL for landing pages (default: http://localhost:8000/api)
$env:AE_PUBLIC_API_URL = "http://localhost:8000/api"

# Console secret (optional for local dev)
$env:AE_CONSOLE_SECRET = ""
```

### Telegram Bot Setup

Already configured! The bot token is stored in the database:

```python
from ae import repo
from ae.enums import ChatProvider

channel = repo.get_chat_channel("acq.db", "ch_demo1_telegram")
print(channel.meta_json.get("telegram_bot_token"))
```

## Troubleshooting

### Port 8000 Already in Use

```powershell
# Check what's using it
.\check_port_8001.ps1

# Kill it
.\check_port_8001.ps1 -Kill
```

### Telegram Bot Not Receiving Messages

1. **Check bot token:**
   ```python
   from ae import repo
   channel = repo.get_chat_channel("acq.db", "ch_demo1_telegram")
   print(channel.meta_json.get("telegram_bot_token"))
   ```

2. **Check server logs:**
   - Should see "[TelegramPolling] Starting polling..."
   - Should see "[TelegramPolling] ✅ Started Telegram customer bot polling"

3. **Test manually:**
   - Send message to bot
   - Check server logs for "Error in poll loop"

### Landing Page Not Found

**Error:** "Page 'p1' not found"

**Solution:**
```bash
# Publish the page first
python -m ae.cli publish-page --db acq.db --page-id p1

# Then visit
http://localhost:8000/pages/p1
```

### Deep Links Not Working

1. **Check landing page:**
   - Verify chat channel is fetched
   - Check browser console for errors
   - Verify `chatChannel.provider === 'telegram'`

2. **Check bot polling:**
   - Verify bot is polling (check server logs)
   - Send `/start package_test123` manually to test

## Development Workflow

### Daily Development

1. **Start server:**
   ```powershell
   .\start_local_dev.ps1
   ```

2. **Make code changes:**
   - Server auto-reloads (if using `--reload`)
   - Telegram polling continues automatically

3. **Test:**
   - Visit landing page
   - Send Telegram message
   - Check Money Board
   - Verify full flow

### Adding New Features

1. **Modify code**
2. **Server auto-reloads**
3. **Test immediately**
4. **No deployment needed**

## Benefits of Local Dev Server

✅ **No ngrok needed** - Everything runs locally
✅ **No webhook setup** - Telegram uses polling
✅ **Fast iteration** - Auto-reload on code changes
✅ **Full stack** - All services in one place
✅ **Easy debugging** - All logs in one place
✅ **Offline capable** - No internet required (except Telegram API)

## Next Steps

1. ✅ **Server running** - `.\start_local_dev.ps1`
2. ⏳ **Test landing page** - Visit `/pages/{page_id}`
3. ⏳ **Test Telegram bot** - Send message to bot
4. ⏳ **Test Money Board** - Open `/money-board`
5. ⏳ **Test full flow** - Landing page → Telegram → Booking

## Production Deployment

When ready for production:
1. Deploy to public server with HTTPS
2. Switch to webhook mode (set webhook URL)
3. Use separate servers for console and public API
4. Configure proper CORS and security

For now, enjoy local development! 🚀
