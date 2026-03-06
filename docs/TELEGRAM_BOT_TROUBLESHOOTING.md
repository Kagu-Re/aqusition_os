# Telegram Bot Troubleshooting Guide

## Common Issues

### Port 8001 Already in Use

**Error:** `[Errno 10048] error while attempting to bind on address ('127.0.0.1', 8001)`

**Solution:**

1. **Check what's using the port:**
   ```powershell
   .\check_port_8001.ps1
   ```

2. **Kill the process:**
   ```powershell
   .\check_port_8001.ps1 -Kill
   ```

3. **Or manually find and kill:**
   ```powershell
   # Find process
   Get-NetTCPConnection -LocalPort 8001 | Select-Object OwningProcess
   
   # Kill process (replace PID with actual process ID)
   Stop-Process -Id <PID> -Force
   ```

4. **Or use a different port:**
   ```powershell
   # Start server on different port
   python -m ae.cli run-public --host 127.0.0.1 --port 8002
   
   # Update ngrok to use new port
   ngrok http 8002
   ```

### ngrok Not Found

**Error:** `CommandNotFoundException: The term 'ngrok' is not recognized`

**Solution:**

1. **Install ngrok:**
   - Download from: https://ngrok.com/download
   - Extract `ngrok.exe` to a folder in your PATH
   - Or use Chocolatey: `choco install ngrok`

2. **Verify installation:**
   ```powershell
   ngrok version
   ```

### Webhook Not Receiving Messages

**Symptoms:**
- Messages sent to bot don't appear in database
- No requests in ngrok dashboard

**Solution:**

1. **Check webhook is set:**
   ```bash
   curl "https://api.telegram.org/bot8149020202:AAHeyDXCBvrRYnWYq_Z-1Z0IFJDkpc97A20/getWebhookInfo"
   ```

2. **Verify webhook URL:**
   - Should be your ngrok HTTPS URL
   - Should include `?db=acq.db` parameter
   - Should be publicly accessible

3. **Test webhook endpoint manually:**
   ```bash
   curl -X POST "https://YOUR_NGROK_URL/api/v1/telegram/webhook?db=acq.db" \
     -H "Content-Type: application/json" \
     -d '{"message": {"chat": {"id": 123}, "text": "test", "message_id": 1}}'
   ```

4. **Check server logs** for errors

5. **Check ngrok dashboard:** http://localhost:4040

### Messages Not Stored in Database

**Symptoms:**
- Webhook receives messages (visible in ngrok)
- But messages don't appear in database

**Solution:**

1. **Check database path:**
   - Verify `?db=acq.db` in webhook URL matches your database file
   - Check database file exists and is writable

2. **Check server logs** for database errors

3. **Verify database schema:**
   ```python
   from ae import db
   db.init_db("acq.db")
   ```

4. **Test database manually:**
   ```python
   from ae.repo_chat_messages import list_messages
   messages = list_messages("acq.db", limit=10)
   print(messages)
   ```

### Bot Token Invalid

**Error:** `401 Unauthorized` or `Invalid token`

**Solution:**

1. **Verify bot token:**
   ```python
   from ae import repo
   channel = repo.get_chat_channel("acq.db", "ch_demo1_telegram")
   print(channel.meta_json.get("telegram_bot_token"))
   ```

2. **Get new token from @BotFather:**
   - Message @BotFather on Telegram
   - Use `/token` command
   - Select your bot
   - Copy new token

3. **Update channel:**
   ```python
   from ae import repo
   from ae.enums import ChatProvider
   
   repo.upsert_chat_channel(
       db_path="acq.db",
       channel_id="ch_demo1_telegram",
       provider=ChatProvider.telegram,
       handle="@massage_thaibot",
       meta_json={"telegram_bot_token": "NEW_TOKEN_HERE"}
   )
   ```

### Deep Links Not Working

**Symptoms:**
- Landing page doesn't redirect to Telegram
- Bot doesn't respond to `/start package_xxx`

**Solution:**

1. **Check landing page:**
   - Verify chat channel is fetched correctly
   - Check browser console for errors
   - Verify `chatChannel.provider === 'telegram'`

2. **Test deep link manually:**
   - Open: `https://t.me/massage_thaibot?start=package_test123`
   - Bot should receive `/start package_test123`

3. **Check webhook handler:**
   - Verify `/start` command is handled
   - Check logs for deep link parsing
   - Verify package_id is extracted correctly

### Server Won't Start

**Symptoms:**
- Server fails to start
- Import errors or module not found

**Solution:**

1. **Set PYTHONPATH:**
   ```powershell
   $env:PYTHONPATH = "src"
   ```

2. **Verify Python path:**
   ```powershell
   python -c "import sys; print(sys.path)"
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Check Python version:**
   ```bash
   python --version
   # Should be 3.11+
   ```

## Quick Diagnostic Commands

### Check Server Status
```powershell
# Check if server is running
curl http://localhost:8001/health

# Check port usage
Get-NetTCPConnection -LocalPort 8001
```

### Check Database
```python
from ae import repo

# Check channel
channel = repo.get_chat_channel("acq.db", "ch_demo1_telegram")
print(channel)

# Check conversations
from ae.repo_chat_conversations import list_conversations
convs = list_conversations("acq.db", limit=10)
print(convs)

# Check messages
from ae.repo_chat_messages import list_messages
msgs = list_messages("acq.db", limit=10)
print(msgs)
```

### Check Webhook
```bash
# Get webhook info
curl "https://api.telegram.org/bot8149020202:AAHeyDXCBvrRYnWYq_Z-1Z0IFJDkpc97A20/getWebhookInfo"

# Delete webhook (to reset)
curl -X POST "https://api.telegram.org/bot8149020202:AAHeyDXCBvrRYnWYq_Z-1Z0IFJDkpc97A20/deleteWebhook"
```

## Getting Help

1. **Check logs:**
   - Server logs (console output)
   - ngrok dashboard: http://localhost:4040
   - Database queries

2. **Test components individually:**
   - Server health endpoint
   - Database connectivity
   - Webhook endpoint
   - Telegram API

3. **Review documentation:**
   - `docs/TELEGRAM_BOT_SETUP.md`
   - `docs/TELEGRAM_BOT_LOCALHOST_TESTING.md`
   - `docs/TELEGRAM_BOT_IMPLEMENTATION_COMPLETE.md`
