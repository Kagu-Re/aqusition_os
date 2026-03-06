#!/usr/bin/env python3
"""Check Telegram bot webhook status."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import httpx
from ae import repo
from ae.enums import ChatProvider


async def check_webhook(token: str, bot_name: str):
    """Check webhook status for a bot."""
    print(f"\n[{bot_name}] Checking webhook status...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.telegram.org/bot{token}/getWebhookInfo"
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("ok"):
                webhook_info = data.get("result", {})
                url = webhook_info.get("url", "")
                pending_count = webhook_info.get("pending_update_count", 0)
                last_error_date = webhook_info.get("last_error_date")
                last_error_message = webhook_info.get("last_error_message")
                
                if url:
                    print(f"  [WARN] Webhook is ACTIVE: {url}")
                    print(f"     Pending updates: {pending_count}")
                    if last_error_date:
                        print(f"     Last error: {last_error_message} (at {last_error_date})")
                    print(f"     [CRITICAL] Polling will NOT work while webhook is active!")
                    print(f"     [ACTION] Delete webhook or disable it to enable polling")
                    return {"has_webhook": True, "url": url, "pending": pending_count}
                else:
                    print(f"  [OK] No webhook set - polling should work")
                    return {"has_webhook": False}
            else:
                print(f"  [ERROR] Failed to get webhook info: {data.get('description')}")
                return {"has_webhook": None, "error": data.get("description")}
    except Exception as e:
        print(f"  [ERROR] Error checking webhook: {e}")
        return {"has_webhook": None, "error": str(e)}


async def main():
    """Check webhook status for all Telegram bots."""
    import os
    db_path = os.getenv("AE_DB_PATH", "acq.db")
    
    print("=" * 60)
    print("Telegram Bot Webhook Status Check")
    print("=" * 60)
    print(f"Database: {db_path}")
    
    channels = repo.list_chat_channels(db_path, provider=ChatProvider.telegram, limit=10)
    
    if not channels:
        print("\n[ERROR] No Telegram channels found")
        sys.exit(1)
    
    print(f"\nFound {len(channels)} Telegram channel(s)\n")
    
    results = []
    for channel in channels:
        token = channel.meta_json.get("telegram_bot_token")
        if not token:
            continue
        
        bot_name = channel.display_name or channel.channel_id
        result = await check_webhook(token, bot_name)
        result["channel"] = bot_name
        results.append(result)
    
    # Summary
    print(f"\n{'=' * 60}")
    print("Summary")
    print(f"{'=' * 60}")
    webhook_bots = [r for r in results if r.get("has_webhook")]
    if webhook_bots:
        print(f"\n[WARN] {len(webhook_bots)} bot(s) have active webhooks:")
        for r in webhook_bots:
            print(f"  - {r['channel']}: {r.get('url', 'unknown')}")
        print(f"\n[ACTION] These bots cannot use polling. Delete webhooks to enable polling.")
    else:
        print(f"\n[OK] No active webhooks found - polling should work for all bots")
    
    sys.exit(0 if not webhook_bots else 1)


if __name__ == "__main__":
    asyncio.run(main())
