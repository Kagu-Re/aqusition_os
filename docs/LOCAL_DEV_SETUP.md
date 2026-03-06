# Local Development Setup - Complete Guide

## Overview

Run everything locally without ngrok! This setup provides:
- **Unified server** on port 8000
- **Telegram polling** (no webhook needed)
- **All services** accessible locally
- **Fast development** cycle

## Architecture

```
┌─────────────────────────────────────┐
│ Local Dev Server (port 8000)        │
│                                     │
│  /console      → Console UI         │
│  /money-board  → Money Board        │
│  /api          → Public API         │
│  /pages/{id}   → Landing Pages       │
│  Background    → Telegram Polling    │
└─────────────────────────────────────┘
         │
         ├─→ Telegram API (polling)
         └─→ Database (acq.db)
```

## Quick Start

### 1. Start the Server

```powershell
.\start_local_dev.ps1
```

**That's it!** Everything starts automatically:
- Console server
- Public API
- Landing page serving
- Telegram bot polling

### 2. Access Services

- **Console:** http://localhost:8000/console
- **Money Board:** http://localhost:8000/money-board
- **Public API:** http://localhost:8000/api
- **Landing Pages:** http://localhost:8000/pages/{page_id}

### 3. Test Telegram Bot

Just send a message to `@massage_thaibot` - no webhook setup needed!

## What's Included

### Console (`/console`)
- Full operator console
- Client management
- Page management
- All admin features

### Money Board (`/money-board`)
- Booking management
- View by status columns
- Send messages
- Update booking status

### Public API (`/api`, `/v1/*`)
- `POST /lead` - Lead intake
- `GET /v1/service-packages` - List packages
- `GET /v1/chat/channel` - Get chat channel
- `POST /v1/event` - Track events
- `GET /v1/qr/generate` - Generate QR codes

### Landing Pages (`/pages/{page_id}`)
- Serves published pages from `exports/static_site/`
- Includes package display
- Deep link support
- Full JavaScript functionality

### Telegram Bots (Background)
- **Customer Bot**: Polls for messages, handles deep links
- **Vendor Bot**: (Future) Booking management via Telegram
- Both use polling mode (no webhook)

## Telegram Polling vs Webhooks

### Polling Mode (Local Dev)
- ✅ No public endpoint needed
- ✅ No ngrok required
- ✅ Works behind firewall
- ✅ Perfect for local dev
- ⚠️ Less efficient (polls every 10 seconds)

### Webhook Mode (Production)
- ✅ More efficient
- ✅ Real-time updates
- ✅ Better for production
- ⚠️ Requires public HTTPS endpoint

**Local dev server uses polling automatically!**

## Testing the Full Flow

### Flow 1: Landing Page → Telegram Bot → Booking

1. **Visit landing page:**
   ```
   http://localhost:8000/pages/p1
   ```

2. **Click package:**
   - Redirects to Telegram bot
   - Deep link: `t.me/massage_thaibot?start=package_pkg123`

3. **Bot receives:**
   - Server logs show message received
   - Bot confirms package selection

4. **Complete booking:**
   - Bot guides through booking flow
   - Booking created in Money Board

### Flow 2: Money Board → Telegram → Customer

1. **Open Money Board:**
   ```
   http://localhost:8000/money-board
   ```

2. **Send message:**
   - Click "Send Package Menu"
   - Message sent via Telegram

3. **Customer receives:**
   - Message appears in Telegram
   - Customer can respond

### Flow 3: Telegram → Money Board

1. **Customer sends message:**
   - Polling picks it up
   - Stored in database
   - Event emitted

2. **View in Money Board:**
   - Conversation visible
   - Messages appear
   - Can respond

## Configuration

### Database

Default: `acq.db` in current directory

Override:
```powershell
$env:AE_DB_PATH = "path/to/acq.db"
```

### Public API URL

Default: `http://localhost:8000/api`

Landing pages use this to fetch packages and chat channels.

### Telegram Bot

Bot token stored in database channel config:
```python
channel.meta_json["telegram_bot_token"]
```

## Troubleshooting

### Server Won't Start

**Port 8000 in use:**
```powershell
.\check_port_8001.ps1 -Kill
# Or use different port:
python -m uvicorn ae.local_dev_server:app --host 127.0.0.1 --port 8001
```

### Telegram Bot Not Working

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
   - Send `/start` to bot
   - Check server logs

### Landing Page Not Found

**Error:** "Page 'p1' not found"

**Solution:**
```bash
# Publish page first
python -m ae.cli publish-page --db acq.db --page-id p1

# Then visit
http://localhost:8000/pages/p1
```

### Packages Not Showing

1. **Check API URL:**
   - Landing page uses `AE_PUBLIC_API_URL`
   - Should be `http://localhost:8000/api`

2. **Check packages exist:**
   ```bash
   curl "http://localhost:8000/v1/service-packages?client_id=demo1&db=acq.db"
   ```

3. **Check client has packages:**
   ```python
   from ae import repo
   packages = repo.list_packages("acq.db", client_id="demo1", active=True)
   print(packages)
   ```

## Development Tips

### Auto-Reload

Server auto-reloads on code changes (if using `--reload`):
```powershell
python -m uvicorn ae.local_dev_server:app --host 127.0.0.1 --port 8000 --reload
```

### Debugging

1. **Check server logs** - All output in one place
2. **Check database** - Messages and conversations stored
3. **Check Telegram** - Messages appear in bot
4. **Check browser console** - Landing page JavaScript

### Testing

1. **Unit tests:**
   ```bash
   pytest tests/
   ```

2. **Integration tests:**
   - Start server
   - Test endpoints
   - Test Telegram flow

3. **Manual testing:**
   - Visit landing page
   - Send Telegram message
   - Check Money Board
   - Verify full flow

## File Structure

```
src/ae/
├── local_dev_server.py      # Unified server
├── telegram_polling.py      # Telegram polling client
├── telegram_delivery.py      # Message delivery
└── console_routes_*.py      # API routes

start_local_dev.ps1           # Startup script
LOCAL_DEV_GUIDE.md            # This guide
```

## Next Steps

1. ✅ **Start server:** `.\start_local_dev.ps1`
2. ⏳ **Publish landing page:** `python -m ae.cli publish-page --db acq.db --page-id p1`
3. ⏳ **Visit landing page:** `http://localhost:8000/pages/p1`
4. ⏳ **Test Telegram bot:** Send message to `@massage_thaibot`
5. ⏳ **Test Money Board:** `http://localhost:8000/money-board`
6. ⏳ **Test full flow:** Landing page → Telegram → Booking

## Benefits

✅ **No ngrok** - Everything local
✅ **No webhook setup** - Polling mode
✅ **Fast development** - Auto-reload
✅ **Full stack** - All services
✅ **Easy debugging** - All logs together
✅ **Offline capable** - No internet (except Telegram API)

Enjoy local development! 🚀
