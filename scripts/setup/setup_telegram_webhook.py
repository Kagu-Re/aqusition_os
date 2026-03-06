#!/usr/bin/env python3
"""Set Telegram webhook URL for the bot.

Usage:
    python scripts/setup/setup_telegram_webhook.py
"""

import sys
import os
import json
import urllib.request
import urllib.error

# Configuration
BOT_TOKEN = "8149020202:AAHeyDXCBvrRYnWYq_Z-1Z0IFJDkpc97A20"
# For localhost testing, use ngrok URL: https://abc123.ngrok-free.app/api/v1/telegram/webhook?db=acq.db
# For production, use your actual domain: https://yourdomain.com/api/v1/telegram/webhook?db=acq.db
WEBHOOK_URL = "https://yourdomain.com/api/v1/telegram/webhook?db=acq.db"  # UPDATE THIS!

def set_webhook(token: str, url: str) -> bool:
    """Set Telegram webhook URL."""
    api_url = f"https://api.telegram.org/bot{token}/setWebhook"
    payload = {"url": url}
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            api_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("ok", False), result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        return False, {"error": error_body, "status": e.code}
    except Exception as e:
        return False, {"error": str(e)}

def get_webhook_info(token: str):
    """Get current webhook info."""
    api_url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
    
    try:
        with urllib.request.urlopen(api_url, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("ok", False), result
    except Exception as e:
        return False, {"error": str(e)}

if __name__ == "__main__":
    print("Telegram Webhook Setup")
    print("=" * 50)
    print(f"Bot Token: {BOT_TOKEN[:20]}...")
    print(f"Webhook URL: {WEBHOOK_URL}")
    print("")
    
    if "yourdomain.com" in WEBHOOK_URL:
        print("⚠️  WARNING: Please update WEBHOOK_URL in this script!")
        print("   Replace 'yourdomain.com' with your actual domain.")
        print("")
        sys.exit(1)
    
    # Get current webhook info
    print("Checking current webhook...")
    ok, info = get_webhook_info(BOT_TOKEN)
    if ok:
        webhook_info = info.get("result", {})
        current_url = webhook_info.get("url", "")
        if current_url:
            print(f"Current webhook URL: {current_url}")
        else:
            print("No webhook currently set")
        print("")
    
    # Set webhook
    print("Setting webhook URL...")
    ok, result = set_webhook(BOT_TOKEN, WEBHOOK_URL)
    
    if ok:
        print("✅ Webhook set successfully!")
        print("")
        print("Next steps:")
        print("1. Send a test message to @massage_thaibot on Telegram")
        print("2. Check your server logs to verify webhook is receiving messages")
        print("3. Test deep link from landing page")
    else:
        print("❌ Failed to set webhook:")
        print(json.dumps(result, indent=2))
        sys.exit(1)
