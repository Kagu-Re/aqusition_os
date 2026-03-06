import sys
# Add src to path (run from project root)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_root, "src"))

from ae.db import connect
import json

con = connect('acq.db')
rows = con.execute('SELECT channel_id, provider, meta_json FROM chat_channels WHERE provider = "telegram"').fetchall()

print(f'\n{"="*60}')
print(f'Found {len(rows)} Telegram channel(s) in database')
print(f'{"="*60}\n')

for i, row in enumerate(rows, 1):
    channel_id, provider, meta_json_str = row
    meta = json.loads(meta_json_str)
    
    print(f'Channel {i}:')
    print(f'  ID: {channel_id}')
    print(f'  Provider: {provider}')
    print(f'  Bot Type: {meta.get("bot_type", "(not set)")}')
    print(f'  Client ID: {meta.get("client_id", "(not set)")}')
    print(f'  Has Token: {"Yes" if meta.get("telegram_bot_token") else "No"}')
    if meta.get("telegram_bot_token"):
        token = meta.get("telegram_bot_token")
        print(f'  Token (masked): {token[:10]}...{token[-10:]}')
    print()

con.close()
