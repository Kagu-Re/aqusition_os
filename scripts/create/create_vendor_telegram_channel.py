"""Create Telegram channel for vendor bot.

Usage:
    python create_vendor_telegram_channel.py
"""

import sys
import os

# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo
from ae.enums import ChatProvider

if __name__ == "__main__":
    db_path = "acq.db"
    client_id = "demo1"  # Vendor bot is for managing bookings, not tied to a specific client
    
    print("Creating vendor Telegram channel...")
    print(f"  Database: {db_path}")
    print(f"  Bot Handle: @vendorthaibot")
    print(f"  Bot Token: 8250433487:AAFtelsTkLUjO56D7T3glHiUz5GC0ibqTKY")
    print("")
    
    # Create vendor channel
    channel = repo.upsert_chat_channel(
        db_path=db_path,
        channel_id="ch_vendor_telegram",
        provider=ChatProvider.telegram,
        handle="@vendorthaibot",
        display_name="Vendor Telegram Bot",
        meta_json={
            "client_id": client_id,
            "telegram_bot_token": "8250433487:AAFtelsTkLUjO56D7T3glHiUz5GC0ibqTKY",
            "bot_type": "vendor"  # Mark as vendor bot
        }
    )
    
    print("[OK] Vendor Telegram channel created!")
    print(f"   Channel ID: {channel.channel_id}")
    print(f"   Handle: {channel.handle}")
    print(f"   Bot Token: {'*' * 20}...{channel.meta_json.get('telegram_bot_token', '')[-10:]}")
    print("")
    print("⚠️  IMPORTANT: Configure vendor_chat_id to receive booking notifications!")
    print("")
    print("To find your Telegram chat ID:")
    print("  1. Start a chat with @userinfobot on Telegram")
    print("  2. It will reply with your user ID")
    print("  3. Run: python set_vendor_chat_id.py --chat-id YOUR_USER_ID")
    print("")
    print("The vendor bot will start automatically when you run:")
    print("  .\\start_local_dev.ps1")
    print("")
    print("Vendor bot commands:")
    print("  /bookings - List pending bookings")
    print("  /confirm <booking_id> - Confirm a booking")
    print("  /paid <payment_id> - Mark payment as paid")
    print("  /complete <booking_id> - Mark booking as completed")
