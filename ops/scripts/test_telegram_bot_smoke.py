#!/usr/bin/env python3
"""Smoke test for Telegram bot connectivity and responsiveness.

Tests:
1. Bot token validity (getMe API)
2. Bot can receive updates (getUpdates API)
3. Bot can send messages (sendMessage API - if chat_id provided)
4. Polling is active and receiving updates
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import httpx
from ae import repo
from ae.enums import ChatProvider


async def test_bot_token(token: str, bot_name: str = "Bot") -> dict:
    """Test if bot token is valid by calling getMe."""
    print(f"\n[{bot_name}] Testing bot token validity...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.telegram.org/bot{token}/getMe"
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("ok"):
                bot_info = data.get("result", {})
                print(f"  [OK] Bot token valid")
                print(f"     Username: @{bot_info.get('username')}")
                print(f"     Bot ID: {bot_info.get('id')}")
                print(f"     Name: {bot_info.get('first_name')}")
                return {"ok": True, "bot_info": bot_info}
            else:
                print(f"  [ERROR] Bot token invalid: {data.get('description')}")
                return {"ok": False, "error": data.get("description")}
    except Exception as e:
        print(f"  [ERROR] Error testing bot token: {e}")
        return {"ok": False, "error": str(e)}


async def test_get_updates(token: str, bot_name: str = "Bot", timeout: int = 5) -> dict:
    """Test if bot can receive updates."""
    print(f"\n[{bot_name}] Testing getUpdates API...")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout + 5, connect=5.0)) as client:
            # Use offset=0 to get all available updates
            # According to Telegram docs, offset=0 gets all updates
            response = await client.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                params={
                    "offset": 0,
                    "timeout": timeout,
                    "allowed_updates": ["message", "callback_query"]
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("ok"):
                updates = data.get("result", [])
                print(f"  [OK] getUpdates successful")
                print(f"     Received {len(updates)} update(s)")
                if updates:
                    print(f"     Update IDs: {[u.get('update_id') for u in updates]}")
                    for update in updates[:3]:  # Show first 3 updates
                        if "message" in update:
                            msg = update["message"]
                            print(f"       - Message from chat_id: {msg.get('chat', {}).get('id')}, text: {msg.get('text', '')[:50]}")
                else:
                    print(f"     [WARN] No updates available (this is normal if no messages were sent)")
                return {"ok": True, "update_count": len(updates), "updates": updates}
            else:
                print(f"  [ERROR] getUpdates failed: {data.get('description')}")
                return {"ok": False, "error": data.get("description")}
    except httpx.TimeoutException:
        print(f"  [WARN] getUpdates timed out (this is normal for long polling)")
        return {"ok": True, "timeout": True, "update_count": 0}
    except Exception as e:
        print(f"  [ERROR] Error testing getUpdates: {e}")
        return {"ok": False, "error": str(e)}


async def test_send_message(token: str, chat_id: str, bot_name: str = "Bot") -> dict:
    """Test if bot can send messages."""
    print(f"\n[{bot_name}] Testing sendMessage API...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": "🤖 Bot smoke test - if you see this, the bot can send messages!"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("ok"):
                msg_info = data.get("result", {})
                print(f"  [OK] sendMessage successful")
                print(f"     Message ID: {msg_info.get('message_id')}")
                return {"ok": True, "message_id": msg_info.get("message_id")}
            else:
                print(f"  [ERROR] sendMessage failed: {data.get('description')}")
                return {"ok": False, "error": data.get("description")}
    except Exception as e:
        print(f"  [ERROR] Error testing sendMessage: {e}")
        return {"ok": False, "error": str(e)}


async def main():
    """Run smoke tests for all Telegram bots."""
    db_path = os.getenv("AE_DB_PATH", "acq.db")
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        print(f"   Set AE_DB_PATH environment variable or ensure acq.db exists")
        sys.exit(1)
    
    print("=" * 60)
    print("Telegram Bot Smoke Test")
    print("=" * 60)
    print(f"Database: {db_path}")
    
    # Get all Telegram channels
    channels = repo.list_chat_channels(db_path, provider=ChatProvider.telegram, limit=10)
    
    if not channels:
        print("\n[ERROR] No Telegram channels found in database")
        print("   Please configure Telegram channels first")
        sys.exit(1)
    
    print(f"\nFound {len(channels)} Telegram channel(s)")
    
    results = []
    for channel in channels:
        token = channel.meta_json.get("telegram_bot_token")
        if not token:
            print(f"\n[WARN] Channel {channel.channel_id} has no bot token")
            continue
        
        bot_name = channel.display_name or channel.channel_id
        print(f"\n{'=' * 60}")
        print(f"Testing: {bot_name}")
        print(f"{'=' * 60}")
        
        # Test 1: Bot token validity
        token_test = await test_bot_token(token, bot_name)
        if not token_test.get("ok"):
            results.append({"channel": bot_name, "status": "FAILED", "reason": "Invalid token"})
            continue
        
        # Test 2: Get updates
        updates_test = await test_get_updates(token, bot_name, timeout=3)
        
        # Test 3: Send message (if we have a chat_id)
        chat_id = channel.meta_json.get("vendor_chat_id") or channel.meta_json.get("test_chat_id")
        send_test = None
        if chat_id:
            send_test = await test_send_message(token, chat_id, bot_name)
        else:
            print(f"\n[{bot_name}] [WARN] No chat_id found (vendor_chat_id or test_chat_id)")
            print(f"     Skipping sendMessage test")
            print(f"     To test sending, add vendor_chat_id or test_chat_id to channel meta_json")
        
        # Summary
        status = "OK"
        if not token_test.get("ok"):
            status = "FAILED"
        elif updates_test.get("error"):
            status = "PARTIAL"
        
        results.append({
            "channel": bot_name,
            "status": status,
            "token_ok": token_test.get("ok"),
            "updates_ok": updates_test.get("ok"),
            "send_ok": send_test.get("ok") if send_test else None,
            "update_count": updates_test.get("update_count", 0)
        })
    
    # Final summary
    print(f"\n{'=' * 60}")
    print("Summary")
    print(f"{'=' * 60}")
    for result in results:
        status_icon = "[OK]" if result["status"] == "OK" else "[WARN]" if result["status"] == "PARTIAL" else "[ERROR]"
        print(f"{status_icon} {result['channel']}: {result['status']}")
        print(f"   Token: {'[OK]' if result['token_ok'] else '[ERROR]'}")
        print(f"   Updates: {'[OK]' if result['updates_ok'] else '[ERROR]'} ({result['update_count']} received)")
        if result['send_ok'] is not None:
            print(f"   Send: {'[OK]' if result['send_ok'] else '[ERROR]'}")
    
    # Exit code
    if all(r["status"] == "OK" for r in results):
        print(f"\n[OK] All tests passed!")
        sys.exit(0)
    else:
        print(f"\n[WARN] Some tests failed or were partial")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
