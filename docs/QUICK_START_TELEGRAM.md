# Quick Start Guide - Telegram Bot Localhost Testing

## Step-by-Step Setup

### Step 1: Stop Any Existing Processes

```powershell
# Stop ngrok if running
.\stop_ngrok.ps1

# Free up port 8001 if needed
.\check_port_8001.ps1 -Kill
```

### Step 2: Start Public API Server

**Option A: Using the script (opens in new window)**
```powershell
.\start_telegram_dev.ps1
```

**Option B: Manual start**
```powershell
# Set PYTHONPATH
$env:PYTHONPATH = "src"

# Start server
python -m ae.cli run-public --host 127.0.0.1 --port 8001
```

**Verify server is running:**
```powershell
curl http://localhost:8001/health
```

### Step 3: Start ngrok Tunnel

**In a NEW terminal window:**

```powershell
.\start_ngrok.ps1
```

Or manually:
```powershell
ngrok http 8001
```

**Keep this terminal open** - ngrok needs to keep running.

### Step 4: Get ngrok URL

**In another terminal (or wait a few seconds after starting ngrok):**

```powershell
.\get_ngrok_url.ps1
```

This will:
- Show your ngrok HTTPS URL
- Show the webhook URL format
- Copy webhook URL to clipboard
- Give you the curl command to set webhook

### Step 5: Set Telegram Webhook

**Copy the webhook URL from Step 4 and use it:**

```powershell
# Replace YOUR_NGROK_URL with the actual URL from get_ngrok_url.ps1
curl -X POST "https://api.telegram.org/bot8149020202:AAHeyDXCBvrRYnWYq_Z-1Z0IFJDkpc97A20/setWebhook" `
  -H "Content-Type: application/json" `
  -d '{"url": "https://YOUR_NGROK_URL/api/v1/telegram/webhook?db=acq.db"}'
```

**Or update `setup_telegram_webhook.py` and run:**
```powershell
python setup_telegram_webhook.py
```

### Step 6: Test

1. **Send a message** to `@massage_thaibot` on Telegram
2. **Check ngrok dashboard:** http://localhost:4040 (should show incoming request)
3. **Check database:** Message should be stored
4. **Check server logs:** Should show webhook received

## Troubleshooting

### ngrok Not Running

**Error:** "Could not connect to ngrok API"

**Solution:**
```powershell
# Start ngrok
.\start_ngrok.ps1

# Or manually
ngrok http 8001
```

### Port 8001 Already in Use

**Error:** `[Errno 10048]` or "Address already in use"

**Solution:**
```powershell
# Check and kill process
.\check_port_8001.ps1 -Kill

# Or use different port
python -m ae.cli run-public --host 127.0.0.1 --port 8002
ngrok http 8002  # Update ngrok to match
```

### ngrok Endpoint Already Online

**Error:** "The endpoint '...' is already online"

**Solution:**
```powershell
# Stop existing ngrok
.\stop_ngrok.ps1

# Start fresh
.\start_ngrok.ps1
```

## Quick Reference

### Terminal 1: API Server
```powershell
$env:PYTHONPATH = "src"
python -m ae.cli run-public --host 127.0.0.1 --port 8001
```

### Terminal 2: ngrok Tunnel
```powershell
ngrok http 8001
```

### Terminal 3: Get URL & Set Webhook
```powershell
# Get URL
.\get_ngrok_url.ps1

# Set webhook (use URL from above)
curl -X POST "https://api.telegram.org/bot8149020202:AAHeyDXCBvrRYnWYq_Z-1Z0IFJDkpc97A20/setWebhook" `
  -H "Content-Type: application/json" `
  -d '{"url": "https://YOUR_NGROK_URL/api/v1/telegram/webhook?db=acq.db"}'
```

## All Helper Scripts

- `start_telegram_dev.ps1` - Start API server + ngrok (all-in-one)
- `start_ngrok.ps1` - Start ngrok tunnel only
- `stop_ngrok.ps1` - Stop all ngrok processes
- `get_ngrok_url.ps1` - Get current ngrok URL
- `check_port_8001.ps1` - Check/kill process on port 8001
- `setup_telegram_webhook.py` - Set webhook URL

## Next Steps After Setup

1. ✅ Server running on localhost:8001
2. ✅ ngrok tunnel active
3. ✅ Webhook URL set in Telegram
4. ⏳ Test by sending message to bot
5. ⏳ Test deep link from landing page
6. ⏳ Test full booking flow
