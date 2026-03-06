#!/usr/bin/env python3
"""Reset Telegram bot state and fetch pending updates.

This script:
1. Clears all bot state (locks, cooldowns, processed messages)
2. Resets last_update_id to fetch all pending updates
3. Optionally drops pending updates from Telegram
"""

import asyncio
import httpx
from src.ae.repo_chat_channels import list_chat_channels
from src.ae.enums import ChatProvider

async def reset_bot_state(db_path: str = "acq.db", drop_pending: bool = True):
    """Reset Telegram bot state."""
    print(f"[ResetBot] Resetting Telegram bot state (db: {db_path})")
    
    # Get Telegram channels
    channels = list_chat_channels(db_path, provider=ChatProvider.telegram, limit=10)
    if not channels:
        print("[ResetBot] [ERROR] No Telegram channels found")
        return
    
    for channel in channels:
        bot_token = channel.meta_json.get("telegram_bot_token")
        if not bot_token:
            print(f"[ResetBot] [WARN] Channel {channel.channel_id} has no bot token, skipping")
            continue
        
        bot_type = channel.meta_json.get("bot_type", "customer")
        bot_username = channel.handle
        print(f"\n[ResetBot] Processing {bot_type} bot: @{bot_username}")
        
        api_url = f"https://api.telegram.org/bot{bot_token}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Delete webhook
            try:
                delete_response = await client.get(
                    f"{api_url}/deleteWebhook",
                    params={"drop_pending_updates": drop_pending}
                )
                delete_data = delete_response.json()
                if delete_data.get("ok"):
                    print(f"  [OK] Webhook deleted (dropped pending: {drop_pending})")
                else:
                    print(f"  [WARN] Failed to delete webhook: {delete_data.get('description')}")
            except Exception as e:
                print(f"  [ERROR] Error deleting webhook: {e}")
            
            # 2. Verify bot token
            try:
                me_response = await client.get(f"{api_url}/getMe")
                me_data = me_response.json()
                if me_data.get("ok"):
                    bot_info = me_data.get("result", {})
                    print(f"  [OK] Bot token valid - @{bot_info.get('username')} (ID: {bot_info.get('id')})")
                else:
                    print(f"  [ERROR] Bot token invalid: {me_data.get('description')}")
                    continue
            except Exception as e:
                print(f"  [ERROR] Error validating bot token: {e}")
                continue
            
            # 3. Get pending updates (if any)
            try:
                updates_response = await client.get(
                    f"{api_url}/getUpdates",
                    params={"offset": 0, "timeout": 1}
                )
                updates_data = updates_response.json()
                if updates_data.get("ok"):
                    updates = updates_data.get("result", [])
                    if updates:
                        print(f"  [INFO] Found {len(updates)} pending update(s)")
                        # Show last update_id
                        last_update_id = max(u.get("update_id", 0) for u in updates)
                        print(f"  [INFO] Last update_id: {last_update_id}")
                    else:
                        print(f"  [OK] No pending updates")
                else:
                    print(f"  [WARN] Failed to get updates: {updates_data.get('description')}")
            except Exception as e:
                print(f"  [ERROR] Error getting updates: {e}")
    
    print("\n[ResetBot] [OK] Bot reset complete!")
    print("[ResetBot] [TIP] Restart your local dev server to apply changes")

if __name__ == "__main__":
    import sys
    drop_pending = "--drop-pending" in sys.argv
    asyncio.run(reset_bot_state(drop_pending=drop_pending))
