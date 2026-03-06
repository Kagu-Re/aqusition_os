# Local Development Setup - Complete Summary

## ✅ What's Been Created

### 1. Unified Local Dev Server (`src/ae/local_dev_server.py`)
- **Single server** on port 8000
- **All services** integrated:
  - Console (Money Board, etc.)
  - Public API
  - Landing pages
  - Telegram bot polling (background)

### 2. Telegram Polling Client (`src/ae/telegram_polling.py`)
- **Polling mode** instead of webhooks
- **No ngrok needed** - polls Telegram API directly
- **Automatic startup** when server starts
- Handles messages, deep links, package selection

### 3. Startup Script (`start_local_dev.ps1`)
- **One command** to start everything
- **Port checking** - detects conflicts
- **Auto-configuration** - sets environment variables
- **Clear output** - shows all available services

### 4. Documentation
- `LOCAL_DEV_GUIDE.md` - Complete guide
- `docs/LOCAL_DEV_SETUP.md` - Detailed setup
- `QUICK_START_LOCAL.md` - Quick reference

## 🚀 How to Use

### Start Everything

```powershell
.\start_local_dev.ps1
```

### Access Services

- **Console:** http://localhost:8000/console
- **Money Board:** http://localhost:8000/money-board
- **Public API:** http://localhost:8000/api
- **Landing Pages:** http://localhost:8000/pages/{page_id}

### Test Telegram Bot

Just send a message to `@massage_thaibot` - no webhook setup needed!

## 🔄 How It Works

### Telegram Polling

Instead of webhooks (which need ngrok), the server:
1. **Polls Telegram API** every 10 seconds
2. **Receives updates** (messages, callbacks)
3. **Processes messages** automatically
4. **Stores in database** and emits events

**No public endpoint needed!**

### Unified Server

Everything runs on **one port (8000)**:
- Console routes → `/console/*`, `/api/*`
- Public API → `/api/*`, `/v1/*`
- Landing pages → `/pages/*`
- Telegram polling → Background task

## 📋 Testing the Full Flow

### Flow 1: Landing Page → Telegram Bot

1. **Publish page:**
   ```bash
   python -m ae.cli publish-page --db acq.db --page-id p1
   ```

2. **Visit:** http://localhost:8000/pages/p1

3. **Click package** → Redirects to Telegram bot

4. **Bot receives** → Confirms package selection

### Flow 2: Money Board → Telegram

1. **Open:** http://localhost:8000/money-board

2. **Send message** → Delivered via Telegram

3. **Customer receives** → Can respond

### Flow 3: Telegram → Money Board

1. **Customer sends message** → Polling picks it up

2. **View in Money Board** → Conversation appears

## 🎯 Key Benefits

✅ **No ngrok** - Everything local
✅ **No webhook setup** - Polling mode
✅ **One command** - Start everything
✅ **Fast development** - Auto-reload
✅ **Full stack** - All services included
✅ **Easy debugging** - All logs together

## 📁 Files Created

```
src/ae/
├── local_dev_server.py      # Unified server
├── telegram_polling.py      # Telegram polling client

start_local_dev.ps1           # Startup script

LOCAL_DEV_GUIDE.md            # Complete guide
QUICK_START_LOCAL.md          # Quick reference
docs/LOCAL_DEV_SETUP.md       # Detailed setup
LOCAL_DEV_SUMMARY.md          # This file
```

## 🔧 Configuration

### Environment Variables

```powershell
# Database path (default: acq.db)
$env:AE_DB_PATH = "acq.db"

# Public API URL (default: http://localhost:8000/api)
$env:AE_PUBLIC_API_URL = "http://localhost:8000/api"
```

### Telegram Bot

Bot token stored in database channel config:
```python
channel.meta_json["telegram_bot_token"]
```

## 🐛 Troubleshooting

### Port 8000 in Use
```powershell
.\check_port_8001.ps1 -Kill
```

### Telegram Bot Not Working
Check server logs for:
- `[TelegramPolling] Starting polling...`
- `[TelegramPolling] ✅ Started Telegram customer bot polling`

### Landing Page Not Found
Publish it first:
```bash
python -m ae.cli publish-page --db acq.db --page-id p1
```

## 📊 Architecture

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

## 🎉 Ready to Develop!

Everything is set up and ready to use. Just run:

```powershell
.\start_local_dev.ps1
```

And start developing! 🚀
