# Telegram Bot Setup Guide

## Quick Setup

### Step 1: Channel Created ✅

The Telegram channel has been created with:
- **Channel ID:** `ch_demo1_telegram`
- **Bot Handle:** `@massage_thaibot`
- **Client ID:** `demo1`
- **Bot Token:** Configured

### Step 2: Set Webhook URL

You need to configure Telegram to send updates to your server.

**Option A: Using the helper script**

1. Edit `setup_telegram_webhook.py` and update `WEBHOOK_URL`:
   ```python
   WEBHOOK_URL = "https://yourdomain.com/api/v1/telegram/webhook?db=acq.db"
   ```
   Replace `yourdomain.com` with your actual domain.

2. Run the script:
   ```bash
   python setup_telegram_webhook.py
   ```

**Option B: Using curl**

```bash
curl -X POST "https://api.telegram.org/bot8149020202:AAHeyDXCBvrRYnWYq_Z-1Z0IFJDkpc97A20/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://yourdomain.com/api/v1/telegram/webhook?db=acq.db"}'
```

**Important:** Replace `yourdomain.com` with your actual public domain where the API is hosted.

### Step 3: Verify Webhook

Check if webhook is set correctly:

```bash
curl "https://api.telegram.org/bot8149020202:AAHeyDXCBvrRYnWYq_Z-1Z0IFJDkpc97A20/getWebhookInfo"
```

You should see:
```json
{
  "ok": true,
  "result": {
    "url": "https://yourdomain.com/api/v1/telegram/webhook?db=acq.db",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

### Step 4: Test

1. **Send a test message:**
   - Open Telegram
   - Search for `@massage_thaibot`
   - Send a message: `/start` or `Hello`

2. **Check server logs:**
   - Verify webhook received the message
   - Check database for stored message
   - Verify conversation was created

3. **Test deep link:**
   - Visit landing page
   - Click on a package
   - Should redirect to Telegram bot with deep link
   - Bot should confirm package selection

## Troubleshooting

### Webhook Not Receiving Messages

1. **Check webhook URL:**
   ```bash
   curl "https://api.telegram.org/bot8149020202:AAHeyDXCBvrRYnWYq_Z-1Z0IFJDkpc97A20/getWebhookInfo"
   ```

2. **Verify HTTPS:**
   - Webhook URL must use HTTPS (not HTTP)
   - SSL certificate must be valid
   - Domain must be publicly accessible

3. **Check firewall:**
   - Ensure port 443 (HTTPS) is open
   - Check security groups/rules

4. **Test endpoint manually:**
   ```bash
   curl -X POST "https://yourdomain.com/api/v1/telegram/webhook?db=acq.db" \
     -H "Content-Type: application/json" \
     -d '{"message": {"chat": {"id": 123}, "text": "test", "message_id": 1}}'
   ```

### Messages Not Stored

1. **Check database:**
   ```sql
   SELECT * FROM chat_messages ORDER BY ts DESC LIMIT 10;
   SELECT * FROM chat_conversations ORDER BY updated_at DESC LIMIT 10;
   ```

2. **Check logs:**
   - Look for errors in webhook handler
   - Check for database connection issues

3. **Verify channel configuration:**
   ```python
   from ae import repo
   channel = repo.get_chat_channel("acq.db", "ch_demo1_telegram")
   print(channel.meta_json.get("telegram_bot_token"))
   ```

### Deep Links Not Working

1. **Check landing page:**
   - Verify chat channel is fetched
   - Check browser console for errors
   - Verify `chatChannel.provider === 'telegram'`

2. **Test deep link manually:**
   - Open: `https://t.me/massage_thaibot?start=package_test123`
   - Bot should receive `/start package_test123`

3. **Check webhook handler:**
   - Verify `/start` command is handled
   - Check logs for deep link parsing

## Configuration Reference

### Channel Configuration

```python
from ae import repo
from ae.enums import ChatProvider

channel = repo.upsert_chat_channel(
    db_path="acq.db",
    channel_id="ch_demo1_telegram",
    provider=ChatProvider.telegram,
    handle="@massage_thaibot",
    display_name="Demo1 Telegram Bot",
    meta_json={
        "client_id": "demo1",
        "telegram_bot_token": "8149020202:AAHeyDXCBvrRYnWYq_Z-1Z0IFJDkpc97A20"
    }
)
```

### Environment Variables (Optional)

If you want to use environment variables instead of storing token in database:

```bash
export TELEGRAM_BOT_TOKEN="8149020202:AAHeyDXCBvrRYnWYq_Z-1Z0IFJDkpc97A20"
```

Note: Currently, the token is stored in channel `meta_json`. Environment variable support can be added if needed.

## Next Steps

1. ✅ Channel created
2. ⏳ Set webhook URL (update `setup_telegram_webhook.py` and run it)
3. ⏳ Test webhook (send message to bot)
4. ⏳ Test deep link (click package on landing page)
5. ⏳ Test full flow (package → booking → payment)

## Support

For issues or questions:
- Check `docs/TELEGRAM_BOT_IMPLEMENTATION_COMPLETE.md` for implementation details
- Check `docs/TELEGRAM_BOT_LEAN_INTEGRATION.md` for design documentation
- Review server logs for errors
- Test each component individually
