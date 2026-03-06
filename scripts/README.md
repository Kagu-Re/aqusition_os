# Scripts

Development and operational scripts. Run from **project root**:

```bash
# From project root
python scripts/setup/setup_demo1_client.py
python scripts/runbooks/clear_stale_conversations.py --db acq.db
```

## Structure

| Directory | Purpose |
|-----------|---------|
| `setup/` | One-time setup (demo client, packages, Telegram webhook, availability) |
| `create/` | Data creation (test clients, pages, channels) |
| `check/` | Inspect and diagnose (bot state, page config, schema, channels) |
| `test/` | Ad-hoc tests (not pytest) |
| `fix/` | One-off fixes and migrations |
| `runbooks/` | Operational tasks (publish, republish, clear, list, show) |
| `shell/` | PowerShell and batch scripts (ngrok, serve, etc.) |

## Common scripts

| Script | Usage |
|--------|-------|
| `setup/setup_demo1_client.py` | Setup massage client + packages + publish (used by `start_local_dev.ps1`) |
| `setup/setup_telegram_webhook.py` | Register webhook URL with Telegram |
| `runbooks/clear_stale_conversations.py` | Clear stale booking state in conversations |
| `runbooks/clear_dev_booking_requests.py` | Remove dev booking requests |
| `create/create_test_client.py` | Create test-massage-spa client with packages |

## Entry points

- **Local dev server**: `.\start_local_dev.ps1` (at project root)
- **Public API only**: `start_public_api.bat` (at project root)

## See also

- `ops/scripts/` — Ops scripts (backup, validation, e2e)
- `docs/FOLDER_STRUCTURE.md` — Full folder layout
