# LINE Integration Guide

This guide walks you through integrating LINE messaging with the Acquisition Engine.

## Step 1: Get LINE Credentials

### 1.1 Access LINE Developers Console

1. Go to **https://developers.line.biz/console/**
2. Log in with your LINE account
3. Select your **Provider** (or create one if you don't have one)

### 1.2 Create a Messaging API Channel

⚠️ **Important**: You need a **Messaging API** channel type, not a "Web app" channel.

**If you already have a "Web app" channel:**
- You need to create a **separate** Messaging API channel for messaging
- Your existing Web app channel cannot be used for messaging

**To create a Messaging API channel:**

1. In LINE Developers Console, click **Create** (or **+** button)
2. Select **Messaging API** (NOT "Web app")
3. Fill in:
   - Channel name (e.g., "ACQ Messaging")
   - Channel description
   - Category (e.g., "Business")
   - Subcategory
4. Accept terms and create

### 1.3 Get Your Credentials

After creating the **Messaging API** channel, you'll see these tabs:

#### **Channel Access Token** (for sending messages)
1. Click on your **Messaging API** channel
2. Look for tabs at the top: **Messaging API**, **Basic settings**, etc.
3. Click the **Messaging API** tab
4. Scroll down to find **Channel access token** section
5. Click **Issue** (or **Reissue** if you already have one)
6. **Copy the token** - it's a long string (100+ characters)
   - ⚠️ **Note**: Copy the entire token, it's just the token string (no "Bearer" prefix)

**If you don't see "Messaging API" tab:**
- Make sure you selected **Messaging API** channel type (not Web app)
- Try refreshing the page
- Check that you're looking at the correct channel

#### **Channel Secret** (for webhook verification)
1. In the same **Messaging API** tab
2. Look for **Channel secret** section (usually near the top)
3. **Copy the secret** - it's shown directly (you already have this: `8b9feb8194fbea8d2435e07d9917bc59`)

#### **Channel ID** (your LINE channel identifier)
1. Click **Basic settings** tab
2. Find **Channel ID** (you already have this: `2009065644`)
3. **Copy the Channel ID**

### 1.4 Enable Webhook

1. In your **Messaging API** channel, go to **Messaging API** tab
2. Scroll to **Webhook settings** section
3. Click **Edit** or **Update**
4. Set **Webhook URL**: `https://yourdomain.com/v1/line/webhook?db=acq.db`
   - For local testing with ngrok: `https://your-ngrok-url.ngrok.io/v1/line/webhook?db=acq.db`
5. Click **Verify** to test the webhook (LINE will send a test event)
6. Enable **Use webhook** toggle/checkbox

**Note**: If you don't see webhook settings, make sure:
- You're in a **Messaging API** channel (not Web app)
- You're in the **Messaging API** tab (not Basic settings)

## Step 2: Configure Authentication (X-AE-SECRET)

### Option A: No Authentication (Local Development)

**Skip authentication** - Leave `AE_CONSOLE_SECRET` unset in `.env`:

```bash
# .env file - leave AE_CONSOLE_SECRET empty or don't include it
# AE_CONSOLE_SECRET=
```

Then API calls work without headers:
```bash
curl -X POST http://localhost:8000/api/chat/channels \
  -H "Content-Type: application/json" \
  -d '{...}'
```

### Option B: Set Authentication (Recommended for Production)

1. **Add to `.env`**:
   ```bash
   AE_CONSOLE_SECRET=your-random-secret-here
   ```

2. **Use in API calls**:
   ```bash
   curl -X POST http://localhost:8000/api/chat/channels \
     -H "Content-Type: application/json" \
     -H "X-AE-SECRET: your-random-secret-here" \
     -d '{...}'
   ```

## Step 3: Register LINE Channel

### Method 1: Via Console API (Recommended)

```bash
curl -X POST http://localhost:8000/api/chat/channels \
  -H "Content-Type: application/json" \
  -H "X-AE-SECRET: your-secret" \
  -d '{
    "channel_id": "line_main",
    "provider": "line",
    "handle": "YOUR_LINE_CHANNEL_ID",
    "display_name": "Main LINE Channel",
    "meta_json": {
      "channel_access_token": "YOUR_CHANNEL_ACCESS_TOKEN",
      "channel_secret": "YOUR_CHANNEL_SECRET"
    }
  }'
```

**Replace:**
- `YOUR_LINE_CHANNEL_ID` - From Basic settings tab
- `YOUR_CHANNEL_ACCESS_TOKEN` - From Messaging API tab (without "Bearer " prefix)
- `YOUR_CHANNEL_SECRET` - From Messaging API tab
- `your-secret` - Your `AE_CONSOLE_SECRET` value (or omit header if not set)

### Method 2: Via Python Script

Create `ops/scripts/setup_line_channel.py`:

```python
#!/usr/bin/env python3
"""Register LINE channel with credentials."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ae import repo
from ae.enums import ChatProvider

# ⚠️ REPLACE THESE WITH YOUR ACTUAL VALUES:
LINE_CHANNEL_ACCESS_TOKEN = "YOUR_CHANNEL_ACCESS_TOKEN_HERE"
LINE_CHANNEL_SECRET = "YOUR_CHANNEL_SECRET_HERE"
LINE_CHANNEL_ID = "YOUR_CHANNEL_ID_HERE"

db_path = "acq.db"  # or your DB path

channel = repo.upsert_chat_channel(
    db_path,
    channel_id="line_main",
    provider=ChatProvider.line,
    handle=LINE_CHANNEL_ID,
    display_name="Main LINE Channel",
    meta_json={
        "channel_access_token": LINE_CHANNEL_ACCESS_TOKEN,
        "channel_secret": LINE_CHANNEL_SECRET,
    },
)

print(f"✅ LINE channel registered: {channel.channel_id}")
print(f"   Provider: {channel.provider.value}")
print(f"   Handle: {channel.handle}")
```

Run it:
```bash
python ops/scripts/setup_line_channel.py
```

## Step 4: Test the Integration

### 4.1 Send a Test Message

1. Open LINE app on your phone
2. Add your LINE bot as a friend (scan QR code from LINE Developers Console)
3. Send a message: "Hello"

### 4.2 Check Database

```bash
# Check if message was received
python -c "
from ae import repo
msgs = repo.list_messages('acq.db', conversation_id='conv_line_XXXXX', limit=10)
for m in msgs:
    print(f'{m.direction}: {m.text}')
"
```

### 4.3 Run Automation

```bash
python -c "
from ae.chat_automation import run_due_chat_automations
from datetime import datetime
sent = run_due_chat_automations('acq.db', now=datetime.utcnow())
print(f'Sent {sent} automated messages')
"
```

## Troubleshooting

### "I don't see Messaging API tab"
- **You created a "Web app" channel instead of "Messaging API" channel**
- Solution: Create a NEW channel and select **Messaging API** (not Web app)
- Web app channels cannot be used for messaging - you need a separate Messaging API channel

### "Can't find Channel Access Token"
- Make sure you created a **Messaging API** channel (not Web app)
- Make sure you're in the **Messaging API** tab (not Basic settings)
- Click **Issue** or **Reissue** button to generate a new token
- The token is long (100+ characters) - make sure you copied it fully
- If you still don't see it, try:
  - Refreshing the page
  - Checking you have the right permissions
  - Looking for "Channel access token" section (might be further down the page)

### "401 Unauthorized" when calling API
- If `AE_CONSOLE_SECRET` is set, you must include `X-AE-SECRET` header
- If not set, remove the header from your API calls
- Check `.env` file is loaded (restart services after changing `.env`)

### "Webhook verification failed"
- Make sure webhook URL is publicly accessible (use ngrok for local testing)
- Check that webhook endpoint is implemented and running
- Verify `channel_secret` matches what's in LINE Developers Console

### "No channel found"
- Make sure you registered the channel via API or script
- Check database: `SELECT * FROM chat_channels WHERE provider='line'`
- Verify `channel_id` matches what you're looking for

## Quick Reference

### LINE Credentials Location

| Credential | Where to Find |
|------------|---------------|
| **Channel Access Token** | LINE Developers Console → **Messaging API** channel (NOT Web app) → **Messaging API** tab → Channel access token section → Click **Issue** |
| **Channel Secret** | LINE Developers Console → **Messaging API** channel → **Messaging API** tab → Channel secret section |
| **Channel ID** | LINE Developers Console → **Messaging API** channel → **Basic settings** tab → Channel ID |

⚠️ **Important**: You MUST create a **Messaging API** channel type. A "Web app" channel will NOT work for messaging.

### X-AE-SECRET Usage

| Scenario | X-AE-SECRET Header |
|----------|-------------------|
| **Local dev, no auth** | Omit header (leave `AE_CONSOLE_SECRET` empty) |
| **Local dev, with auth** | Include: `X-AE-SECRET: <value-from-env>` |
| **Production** | **Required**: `X-AE-SECRET: <value-from-env>` |

## Next Steps

After setting up LINE integration:
1. ✅ Test receiving messages from LINE
2. ✅ Test sending automated responses
3. ✅ Configure chat automation templates
4. ✅ Link conversations to leads
5. ✅ Set up webhook for production deployment
