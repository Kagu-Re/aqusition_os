"""Set vendor_chat_id for vendor Telegram bot channel.

The vendor_chat_id is the Telegram chat ID where booking notifications should be sent.
This is typically your personal Telegram user ID or a group chat ID.

To find your Telegram chat ID:
1. Start a chat with @userinfobot on Telegram
2. It will reply with your user ID
3. Use that ID as the vendor_chat_id

Usage:
    python set_vendor_chat_id.py --chat-id YOUR_TELEGRAM_CHAT_ID
"""

import sys
import os

# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Set vendor_chat_id for vendor Telegram bot")
    parser.add_argument("--chat-id", required=True, help="Telegram chat ID where notifications should be sent")
    parser.add_argument("--db", default="acq.db", help="Database path (default: acq.db)")
    
    args = parser.parse_args()
    
    db_path = args.db
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found: {db_path}")
        sys.exit(1)
    
    # Get existing vendor channel
    channel = repo.get_chat_channel(db_path, "ch_vendor_telegram")
    if not channel:
        print("[ERROR] Vendor channel 'ch_vendor_telegram' not found!")
        print("Run 'python create_vendor_telegram_channel.py' first.")
        sys.exit(1)
    
    # Update meta_json with vendor_chat_id
    meta_json = channel.meta_json.copy()
    meta_json["vendor_chat_id"] = args.chat_id
    
    # Update channel
    updated_channel = repo.upsert_chat_channel(
        db_path=db_path,
        channel_id="ch_vendor_telegram",
        provider=channel.provider,
        handle=channel.handle,
        display_name=channel.display_name,
        meta_json=meta_json
    )
    
    print("[OK] Vendor chat ID configured!")
    print(f"   Channel ID: {updated_channel.channel_id}")
    print(f"   Vendor Chat ID: {updated_channel.meta_json.get('vendor_chat_id')}")
    print("")
    print("The vendor bot will now receive booking notifications at this chat ID.")
    print("Restart the dev server for changes to take effect.")
