#!/usr/bin/env python3
"""Create a Telegram chat channel for demo1 client."""

import sys
import os
# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae import repo
from ae.enums import ChatProvider

db_path = 'acq.db'
client_id = 'demo1'

# Create Telegram channel with bot token
channel = repo.upsert_chat_channel(
    db_path=db_path,
    channel_id='ch_demo1_telegram',
    provider=ChatProvider.telegram,
    handle='@massage_thaibot',
    display_name='Demo1 Telegram Bot',
    meta_json={
        'client_id': client_id,
        'telegram_bot_token': '<REDACTED_TELEGRAM_BOT_TOKEN>'
    }
)

print('[OK] Telegram channel created:')
print(f'   Channel ID: {channel.channel_id}')
print(f'   Provider: {channel.provider}')
print(f'   Handle: {channel.handle}')
handle_clean = channel.handle.replace('@', '')
print(f'   Chat URL: https://t.me/{handle_clean}')
print(f'   Webhook URL: https://t.me/{handle_clean}?start=package_xxx')
print(f'   Client ID: {client_id}')
print(f'   Bot Token: {"*" * 20}...{channel.meta_json.get("telegram_bot_token", "")[-10:]}')
print('')
print('Next steps:')
print('1. Set webhook URL:')
print(f'   curl -X POST "https://api.telegram.org/bot{channel.meta_json.get("telegram_bot_token")}/setWebhook" \\')
print(f'     -H "Content-Type: application/json" \\')
print(f'     -d \'{{"url": "https://yourdomain.com/api/v1/telegram/webhook?db={db_path}"}}\'')
print('')
print('2. Test by sending a message to @massage_thaibot on Telegram')
print('')
print('3. Test deep link from landing page (package selection will redirect to Telegram)')
