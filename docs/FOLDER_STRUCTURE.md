# Folder Structure — Review and Management

This document reviews the project root and proposes a managed structure to reduce clutter and improve discoverability.

---

## 1. Current Root Layout

### 1.1 Directories

| Directory   | Purpose                    | Git status / notes                    |
|-------------|----------------------------|---------------------------------------|
| `src/`      | Application code           | Core package `ae`                     |
| `tests/`    | Pytest tests               | Standard                              |
| `docs/`     | Documentation              | 40+ markdown files                    |
| `ops/`      | Operations, scripts, config| Scripts, runbooks, releases            |
| `clients/`  | Per-client onboarding docs | `demo1/onboarding/*.md`                |
| `accounting/` | Invoices, ledger, receipts| Business-specific; consider data/     |
| `config/`   | Guardrails, QR outputs     | `guardrails.json`, `qr/`              |
| `generated/`| Menu/QR outputs            | Used by `console_routes_menus`        |
| `data/`     | Runtime data (DB, etc.)    | In .gitignore                         |
| `exports/`  | Published pages, payloads  | In .gitignore                         |
| `.github/`  | CI workflows               | Standard                              |
| `.cursor/`  | Cursor IDE                 | Local                                 |

### 1.2 Build / Config Files (Keep at Root)

| File                 | Purpose          |
|----------------------|------------------|
| `pyproject.toml`     | Package config   |
| `requirements.txt`   | Dependencies     |
| `package.json`       | Tailwind / Node  |
| `tailwind.config.js` | Tailwind config  |
| `.gitignore`         |                  |
| `.dockerignore`      |                  |
| `.env.example`       | Env template     |
| `docker-compose*.yml`| Docker           |
| `Dockerfile`         |                  |

### 1.3 Root Clutter — Scripts (~45 Python Files)

**Setup / bootstrap**
- `setup_demo1_client.py`, `setup_packages_for_demo1.py`, `setup_telegram_webhook.py`, `setup_availability.py`

**Create / one-off**
- `create_test_client.py`, `create_test_data.py`, `create_test_page.py`, `create_client_pages.py`, `create_packages_for_demo1.py`, `create_telegram_channel.py`, `create_vendor_telegram_channel.py`

**Check / inspect / debug**
- `check_bot_state.py`, `check_page_config.py`, `check_port_8001.ps1`, `check_package_events.py`, `check_schema.py`, `check_telegram_channels.py`
- `inspect_availability.py`, `inspect_lead.py`, `debug_logic.py`, `debug_money_board.py`, `diagnose_imports.py`

**Test / verify (ad-hoc, not pytest)**
- `test_api_flow.py`, `test_availability_display.py`, `test_booking_v2.py`, `test_chat_channel.py`, `test_full_flow.py`, `test_package_filtering.py`, `test_packages_api.py`, `test_page_content.py`, `test_state_machine.py`
- `verify_all_page_types.py`

**Fix / migrate**
- `fix_client_business_model.py`, `fix_telegram_webhook.py`, `migrate_client_schema.py`, `apply_migrations.py`

**Other**
- `clear_dev_booking_requests.py`, `clear_conversation_state.py`, `clear_stale_conversations.py`
- `demonstrate_content_personalization.py`, `personalize_packages.py`
- `publish_landing_page.py`, `republish_pages.py`
- `list_client_pages.py`, `list_clients_and_templates.py`
- `show_content_differences.py`, `show_package_assignments.py`, `show_page_urls.py`
- `assign_package_focus.py`, `reset_telegram_bot.py`, `set_vendor_chat_id.py`
- `switch_page_template.py`, `update_page_to_massage_client.py`

**Shell**
- `start_local_dev.ps1`, `start_ngrok.ps1`, `start_public_api.bat`, `start_service_package_test.bat`, `start_telegram_dev.ps1`
- `stop_ngrok.ps1`, `serve_pages.bat`
- `check_port_8001.ps1`, `get_ngrok_url.ps1`

### 1.4 Root Clutter — Markdown Docs (~12 at Root)

- `BACKEND_INTEGRATION_ANALYSIS.md`, `CONTENT_PERSONALIZATION_SUMMARY.md`, `EXPECTED_PREMIUM_PAGE_CONTENT.md`
- `LOCAL_DEV_GUIDE.md`, `LOCAL_DEV_SUMMARY.md`, `QUICK_START_LOCAL.md`, `QUICK_START_TELEGRAM.md`
- `README.md`, `README_v1_1_Pilot.md`, `STARTUP_SUMMARY.md`
- `VENDOR_BOT_SETUP.md`, `VENDOR_BOT_SUMMARY.md`

### 1.5 Runtime / Artifacts (Should Be Ignored)

- `acq.db`, `debug_api.log`, `demo_output.txt` — runtime
- `acq_engine_v7_8_0_op_crm_001c.zip` — release artifact

---

## 2. Problems

1. **Root pollution**: 45+ scripts and 12+ markdown files at root reduce clarity.
2. **Overlap with `ops/scripts`**: `ops/scripts` has similar utilities (test, validate, publish); root scripts could migrate.
3. **Docs scattered**: Some docs at root duplicate or overlap with `docs/`.
4. **Unclear ownership**: Hard to tell setup vs one-off vs supported tooling.

---

## 3. Proposed Managed Structure

### 3.1 Keep at Root

```
README.md
CHANGELOG.md
pyproject.toml
requirements.txt
package.json
tailwind.config.js
.env.example
.gitignore
.dockerignore
Dockerfile
docker-compose.yml
docker-compose.reverse-proxy.yml
```

Plus startup entry points only:

```
start_local_dev.ps1      # Primary dev entry
start_public_api.bat      # If used
```

### 3.2 Move Scripts → `scripts/`

Create `scripts/` (or expand `ops/scripts`) to hold dev/setup utilities:

```
scripts/
├── setup/           # One-time setup
│   ├── demo1_client.py
│   ├── demo1_packages.py
│   ├── telegram_webhook.py
│   └── availability.py
├── create/          # Data creation
│   ├── test_client.py
│   ├── test_data.py
│   ├── client_pages.py
│   └── vendor_channel.py
├── check/           # Inspect / diagnose
│   ├── bot_state.py
│   ├── page_config.py
│   ├── telegram_channels.py
│   └── schema.py
├── test/            # Ad-hoc (non-pytest) tests
│   ├── api_flow.py
│   ├── full_flow.py
│   └── availability_display.py
├── fix/             # One-off fixes / migrations
│   ├── client_business_model.py
│   └── telegram_webhook.py
└── runbooks/        # Operational scripts
    ├── publish_landing_page.py
    ├── republish_pages.py
    └── apply_migrations.py
```

**Alternative:** Fold into `ops/scripts` with subdirs (`ops/scripts/setup/`, etc.) to avoid a second scripts root.

### 3.3 Move Docs → `docs/`

| From root                     | To `docs/`                        |
|-------------------------------|-----------------------------------|
| `LOCAL_DEV_GUIDE.md`          | `docs/LOCAL_DEV_GUIDE.md`         |
| `LOCAL_DEV_SUMMARY.md`        | `docs/LOCAL_DEV_SUMMARY.md`       |
| `QUICK_START_*.md`            | `docs/QUICK_START_*.md`           |
| `VENDOR_BOT_*.md`             | `docs/VENDOR_BOT_*.md`            |
| `BACKEND_INTEGRATION_ANALYSIS.md` | `docs/BACKEND_INTEGRATION_ANALYSIS.md` |
| `CONTENT_PERSONALIZATION_SUMMARY.md` | `docs/CONTENT_PERSONALIZATION_SUMMARY.md` |
| etc.                          | `docs/<name>.md`                  |

Keep only `README.md` and `CHANGELOG.md` at root.

### 3.4 Data and Generated Paths

| Path          | Purpose              | Action                          |
|---------------|----------------------|---------------------------------|
| `data/`       | DB, runtime          | Already in .gitignore           |
| `exports/`    | Published output     | Already in .gitignore           |
| `generated/`  | QR, menus            | Add to .gitignore if not committed |
| `accounting/` | Business data        | Add to .gitignore or move to `data/accounting` |
| `config/qr/`  | QR outputs           | Clarify vs `generated/qr`       |

### 3.5 Consolidate `config/` and `generated/`

- `config/` → app/config (guardrails.json, etc.)
- `generated/` → build/runtime output (QR, menus) — add to .gitignore
- Code references: `console_routes_menus` uses `generated/menus`, `generated/qr`

---

## 4. Target Root (After Reorg)

```
aqusition_os/
├── README.md
├── CHANGELOG.md
├── pyproject.toml
├── requirements.txt
├── package.json
├── tailwind.config.js
├── .env.example
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── docker-compose.reverse-proxy.yml
├── start_local_dev.ps1
├── start_public_api.bat
├── src/
├── tests/
├── docs/
├── ops/
├── scripts/          # or ops/scripts with subdirs
├── clients/
├── config/
├── data/             # .gitignore
├── exports/          # .gitignore
└── generated/        # .gitignore
```

---

## 5. Migration Plan

| Phase | Action | Status |
|-------|--------|--------|
| 1 | Add `generated/`, `*.log`, etc. to `.gitignore` | ✅ Done |
| 2 | Create `scripts/` and move root `.py` scripts | ✅ Done |
| 3 | Move root `.md` docs → `docs/` | ✅ Done |
| 4 | Move shell scripts (except start_local_dev, start_public_api) → `scripts/shell/` | ✅ Done |
| 5 | Update README, docs with new paths | ✅ Done |
| 6 | Add `scripts/README.md` | ✅ Done |

---

## 6. References

- `ops/scripts/README.md` — existing ops scripts
- `console_routes_menus.py` — uses `generated/menus`, `generated/qr`
- `ops/CONFIG_REFERENCE.md` — `AE_*` env vars
