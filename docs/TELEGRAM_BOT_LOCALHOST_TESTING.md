# Telegram Bot Localhost Testing Guide

## Overview

Telegram webhooks require a **publicly accessible HTTPS endpoint**. For local development, we'll use **ngrok** (or similar tunneling service) to expose your localhost server to the internet.

## Option 1: Using ngrok (Recommended)

### Step 1: Install ngrok

**Windows:**
1. Download from https://ngrok.com/download
2. Extract `ngrok.exe` to a folder in your PATH
3. Or use Chocolatey: `choco install ngrok`

**macOS:**
```bash
brew install ngrok
```

**Linux:**
```bash
# Download from https://ngrok.com/download
# Or use snap: snap install ngrok
```

### Step 2: Start Public API Server

Start your public API server on localhost:

```bash
# Set PYTHONPATH
set PYTHONPATH=src  # Windows
# or
export PYTHONPATH=src  # Linux/macOS

# Start public API server
python -m ae.cli run-public --host 127.0.0.1 --port 8001
```

Or use the provided script:
```bash
# Windows
.\ops\scripts\start_public_api.ps1

# Linux/macOS
bash ops/scripts/start_public_api.sh
```

Verify it's running:
```bash
curl http://localhost:8001/health
```

### Step 3: Start ngrok Tunnel

Open a **new terminal** and run:

```bash
ngrok http 8001
```

You'll see output like:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8001
```

**Copy the HTTPS URL** (e.g., `https://abc123.ngrok-free.app`)

### Step 4: Set Telegram Webhook

Use the ngrok URL to set the webhook:

```bash
curl -X POST "https://api.telegram.org/bot<REDACTED_TELEGRAM_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://abc123.ngrok-free.app/api/v1/telegram/webhook?db=acq.db"}'
```

**Important:** Replace `abc123.ngrok-free.app` with your actual ngrok URL.

### Step 5: Verify Webhook

Check if webhook is set correctly:

```bash
curl "https://api.telegram.org/bot<REDACTED_TELEGRAM_BOT_TOKEN>/getWebhookInfo"
```

### Step 6: Test

1. **Send a message** to `@massage_thaibot` on Telegram
2. **Check ngrok dashboard** at http://localhost:4040 (shows incoming requests)
3. **Check server logs** to verify webhook received the message
4. **Check database** - message should be stored

## Option 2: Using localtunnel (Alternative)

### Step 1: Install localtunnel

```bash
npm install -g localtunnel
```

### Step 2: Start Public API Server

Same as Option 1, Step 2.

### Step 3: Start Tunnel

```bash
lt --port 8001 --subdomain your-unique-name
```

You'll get a URL like: `https://your-unique-name.loca.lt`

### Step 4: Set Webhook

```bash
curl -X POST "https://api.telegram.org/bot<REDACTED_TELEGRAM_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-unique-name.loca.lt/api/v1/telegram/webhook?db=acq.db"}'
```

## Option 3: Using Cloudflare Tunnel (Free)

### Step 1: Install cloudflared

Download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/

### Step 2: Start Tunnel

```bash
cloudflared tunnel --url http://localhost:8001
```

### Step 3: Set Webhook

Use the provided URL (similar to ngrok).

## Quick Start Script

Create `start_telegram_dev.ps1` (Windows) or `start_telegram_dev.sh` (Linux/macOS):

### Windows (`start_telegram_dev.ps1`)

```powershell
# Start Public API Server
Write-Host "Starting Public API server..." -ForegroundColor Green
$env:PYTHONPATH = "src"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m ae.cli run-public --host 127.0.0.1 --port 8001"

# Wait for server to start
Start-Sleep -Seconds 3

# Start ngrok
Write-Host "Starting ngrok tunnel..." -ForegroundColor Green
Write-Host "Copy the HTTPS URL and use it to set webhook" -ForegroundColor Yellow
ngrok http 8001
```

### Linux/macOS (`start_telegram_dev.sh`)

```bash
#!/bin/bash
# Start Public API Server
echo "Starting Public API server..."
export PYTHONPATH=src
python -m ae.cli run-public --host 127.0.0.1 --port 8001 &
API_PID=$!

# Wait for server to start
sleep 3

# Start ngrok
echo "Starting ngrok tunnel..."
echo "Copy the HTTPS URL and use it to set webhook"
ngrok http 8001

# Cleanup
kill $API_PID
```

## Testing Checklist

### 1. Server Running
- [ ] Public API server running on `http://localhost:8001`
- [ ] Health check works: `curl http://localhost:8001/health`

### 2. Tunnel Active
- [ ] ngrok/localtunnel running
- [ ] HTTPS URL accessible from internet
- [ ] Tunnel forwarding to localhost:8001

### 3. Webhook Configured
- [ ] Webhook URL set in Telegram
- [ ] Webhook info shows correct URL
- [ ] No pending updates

### 4. Message Flow
- [ ] Send message to bot
- [ ] Webhook receives message (check ngrok dashboard)
- [ ] Message stored in database
- [ ] Conversation created
- [ ] Event emitted

### 5. Deep Link
- [ ] Landing page generates deep link
- [ ] Deep link opens Telegram bot
- [ ] Bot receives `/start package_xxx`
- [ ] Package confirmation sent

## Troubleshooting

### ngrok URL Changes Every Time

**Solution:** Use ngrok authtoken for persistent URLs:

```bash
ngrok authtoken YOUR_AUTH_TOKEN
ngrok http 8001 --domain=your-static-domain.ngrok-free.app
```

### Webhook Not Receiving Messages

1. **Check tunnel is active:**
   - Visit ngrok dashboard: http://localhost:4040
   - Should show incoming requests

2. **Test webhook endpoint manually:**
   ```bash
   curl -X POST "https://your-ngrok-url.ngrok-free.app/api/v1/telegram/webhook?db=acq.db" \
     -H "Content-Type: application/json" \
     -d '{"message": {"chat": {"id": 123}, "text": "test", "message_id": 1}}'
   ```

3. **Check webhook URL:**
   ```bash
   curl "https://api.telegram.org/bot<REDACTED_TELEGRAM_BOT_TOKEN>/getWebhookInfo"
   ```

### Server Not Responding

1. **Check server is running:**
   ```bash
   curl http://localhost:8001/health
   ```

2. **Check server logs** for errors

3. **Verify database path** in webhook URL (`?db=acq.db`)

### Database Path Issues

Make sure the `db` parameter in webhook URL matches your database file:

```bash
# If database is in current directory
?db=acq.db

# If database is in specific path
?db=/path/to/acq.db

# Or use absolute path
?db=D:\aqusition_os\acq.db
```

## Development Workflow

### Daily Development

1. **Start server:**
   ```bash
   python -m ae.cli run-public --host 127.0.0.1 --port 8001
   ```

2. **Start tunnel:**
   ```bash
   ngrok http 8001
   ```

3. **Set webhook** (only needed once per ngrok session):
   ```bash
   # Use the ngrok URL from step 2
   curl -X POST "https://api.telegram.org/bot<REDACTED_TELEGRAM_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://YOUR_NGROK_URL/api/v1/telegram/webhook?db=acq.db"}'
   ```

4. **Test and develop:**
   - Make code changes
   - Server auto-reloads (if using `--reload`)
   - Test via Telegram bot

### Production Deployment

When ready for production:
1. Deploy to public server with HTTPS
2. Set webhook to production URL
3. Remove ngrok dependency

## Notes

- **ngrok free tier:** URLs change on restart (use authtoken for static URLs)
- **localtunnel:** May require clicking through browser warning
- **Cloudflare Tunnel:** Most reliable, free, persistent URLs
- **Development only:** Don't use tunnels in production

## Quick Reference

```bash
# Start server
python -m ae.cli run-public --host 127.0.0.1 --port 8001

# Start ngrok (in another terminal)
ngrok http 8001

# Set webhook (replace YOUR_NGROK_URL)
curl -X POST "https://api.telegram.org/bot<REDACTED_TELEGRAM_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://YOUR_NGROK_URL/api/v1/telegram/webhook?db=acq.db"}'

# Verify webhook
curl "https://api.telegram.org/bot<REDACTED_TELEGRAM_BOT_TOKEN>/getWebhookInfo"

# Test endpoint manually
curl -X POST "https://YOUR_NGROK_URL/api/v1/telegram/webhook?db=acq.db" \
  -H "Content-Type: application/json" \
  -d '{"message": {"chat": {"id": 123}, "text": "test", "message_id": 1}}'
```
