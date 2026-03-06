"""
Force delete Telegram webhook and verify it's removed.
Run this if you're getting 409 Conflict errors in polling mode.
"""
import httpx
import asyncio
import sys

# Bot token from your telegram_polling.py logs
BOT_TOKEN = "8250433487:AAFtelsTkLUjO56D7T3glHiUz5GC0ibqTKY"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

async def force_delete_webhook():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Check current webhook status
        print("1. Checking current webhook status...")
        info_response = await client.get(f"{API_URL}/getWebhookInfo")
        info_data = info_response.json()
        
        if info_data.get("ok"):
            webhook_info = info_data.get("result", {})
            webhook_url = webhook_info.get("url", "")
            pending_count = webhook_info.get("pending_update_count", 0)
            
            print(f"   Current webhook URL: {webhook_url or '(none)'}")
            print(f"   Pending updates: {pending_count}")
            
            if not webhook_url:
                print("\n✅ No webhook is set! Polling should work fine.")
                return
        else:
            print(f"   ❌ Error getting webhook info: {info_data}")
            return
        
        # 2. Delete webhook with drop_pending_updates=True
        print("\n2. Deleting webhook and dropping pending updates...")
        delete_response = await client.post(
            f"{API_URL}/deleteWebhook",
            json={"drop_pending_updates": True}
        )
        delete_data = delete_response.json()
        
        if delete_data.get("ok"):
            print("   ✅ Webhook deletion request successful")
        else:
            print(f"   ❌ Webhook deletion failed: {delete_data}")
            return
        
        # 3. Wait for Telegram to process
        print("\n3. Waiting 3 seconds for Telegram to process...")
        await asyncio.sleep(3)
        
        # 4. Verify webhook is deleted
        print("\n4. Verifying webhook is deleted...")
        verify_response = await client.get(f"{API_URL}/getWebhookInfo")
        verify_data = verify_response.json()
        
        if verify_data.get("ok"):
            verify_info = verify_data.get("result", {})
            verify_url = verify_info.get("url", "")
            
            if verify_url:
                print(f"   ❌ WEBHOOK STILL ACTIVE: {verify_url}")
                print("\n⚠️  The webhook keeps getting recreated!")
                print("   Possible causes:")
                print("   - Another bot instance is running")
                print("   - External service (ngrok, webhook server) is setting it")
                print("   - Telegram API delay (rare)")
                print("\n   Try:")
                print("   1. Stop ALL running instances of your bot")
                print("   2. Run this script again")
                print("   3. Check if any webhook services are running")
            else:
                print("   ✅ WEBHOOK SUCCESSFULLY DELETED!")
                print("\n✅ Polling mode should now work without 409 errors.")
                print("   You can restart your local dev server.")
        else:
            print(f"   ❌ Error verifying: {verify_data}")

if __name__ == "__main__":
    print("=" * 60)
    print("Telegram Webhook Force Delete Tool")
    print("=" * 60)
    print()
    
    asyncio.run(force_delete_webhook())
    
    print("\n" + "=" * 60)
