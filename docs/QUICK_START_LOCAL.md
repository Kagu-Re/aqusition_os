# Quick Start - Local Development (No ngrok!)

## One Command to Rule Them All

```powershell
.\start_local_dev.ps1
```

**That's it!** Everything starts:
- ✅ Console (Money Board, etc.)
- ✅ Public API
- ✅ Landing Pages
- ✅ Telegram Bots (polling mode)

## What You Get

### Services Available

- **Console:** http://localhost:8000/console
- **Money Board:** http://localhost:8000/money-board
- **Public API:** http://localhost:8000/api
- **Landing Pages:** http://localhost:8000/pages/{page_id}
- **Telegram Bots:** Automatic polling (no setup needed!)

## How It Works

### Telegram Polling (No Webhook!)

Instead of webhooks (which need ngrok), the server **polls Telegram API** for new messages:
- Server asks Telegram: "Any new messages?"
- Telegram responds with updates
- Server processes messages
- **No public endpoint needed!**

### Unified Server

Everything runs on **one port (8000)**:
- Console routes → `/console/*`
- Public API → `/api/*` and `/v1/*`
- Landing pages → `/pages/*`
- Telegram polling → Background task

## Testing the Flow

### 1. Landing Page → Telegram Bot

1. **Publish a page:**
   ```bash
   python -m ae.cli publish-page --db acq.db --page-id p1
   ```

2. **Visit:** http://localhost:8000/pages/p1

3. **Click package** → Redirects to Telegram bot

4. **Bot receives** → Confirms package selection

### 2. Money Board → Telegram

1. **Open:** http://localhost:8000/money-board

2. **Send message** → Delivered via Telegram

3. **Customer receives** → Can respond

### 3. Telegram → Money Board

1. **Customer sends message** → Polling picks it up

2. **View in Money Board** → Conversation appears

## Configuration

### Database
Default: `acq.db` in current directory

### Telegram Bot
Already configured! Token stored in database channel.

### Public API URL
Default: `http://localhost:8000/api` (automatically set)

## Troubleshooting

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

## Benefits

✅ **No ngrok** - Everything local
✅ **No webhook setup** - Polling mode
✅ **One command** - Start everything
✅ **Fast development** - Auto-reload
✅ **Full stack** - All services included

## Next Steps

1. ✅ **Start server:** `.\start_local_dev.ps1`
2. ⏳ **Test landing page:** Visit `/pages/{page_id}`
3. ⏳ **Test Telegram bot:** Send message to `@massage_thaibot`
4. ⏳ **Test Money Board:** Open `/money-board`
5. ⏳ **Test full flow:** End-to-end booking

Ready to develop! 🚀
