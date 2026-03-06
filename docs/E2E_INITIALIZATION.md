# End-to-End Initialization and Testing Guide

This guide walks you through the complete initialization and testing process for the Acquisition Engine system before launch.

## Overview

The end-to-end initialization script (`ops/scripts/e2e_init_and_test.py`) performs:

1. **Prerequisites check** - Verifies Python version and dependencies
2. **Database initialization** - Creates SQLite schema
3. **Demo data creation** - Sets up template, client, and page
4. **Chat channel setup** - Creates WhatsApp chat channel
5. **Menu setup** - Creates demo menu with sections and items
6. **QR code generation** - Tests QR code generation for menus
7. **Ads integration** - Tests Meta/Google ads adapters (stubs)
8. **Page validation** - Validates the created page
9. **Publish test** - Tests page publishing workflow
10. **Admin user creation** - Creates console admin user
11. **Unit tests** - Runs full test suite
12. **Compliance checks** - Validates aliases and guardrails
13. **Console startup test** - Verifies console app loads
14. **Smoke tests** - Tests API endpoints (if console running)

## Quick Start

### Linux/macOS

```bash
# Make script executable
chmod +x ops/scripts/e2e_init_and_test.py

# Run full initialization and testing
python ops/scripts/e2e_init_and_test.py

# With custom database path
python ops/scripts/e2e_init_and_test.py --db-path /path/to/acq.db

# Skip tests (faster, for quick setup)
python ops/scripts/e2e_init_and_test.py --skip-tests

# Skip console and smoke tests
python ops/scripts/e2e_init_and_test.py --skip-console --skip-smoke
```

### Windows

```batch
REM Run full initialization
python ops\scripts\e2e_init_and_test.py

REM Or use batch wrapper
ops\scripts\e2e_init_and_test.bat
```

## Prerequisites

Before running the initialization script:

1. **Python 3.10+** installed
2. **Dependencies installed**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Database directory** exists (or will be created)

**Note**: The `ae` module is in the `src/` directory. To run CLI commands directly, either:
- Use the wrapper scripts: `ops/scripts/ae_cli.bat` (Windows) or `ops/scripts/ae_cli.sh` (Linux/macOS)
- Set `PYTHONPATH=src` before running commands
- Install the package: `pip install -e .`

## Step-by-Step Manual Process

If you prefer to run steps manually:

### 1. Initialize Database

```bash
python -m ae.cli init-db --db acq.db
```

### 2. Create Template

```bash
python -m ae.cli create-template \
  --db acq.db \
  --template-id trade_lp \
  --version 1.0.0 \
  --cms-schema 1.0 \
  --events 1.0
```

### 3. Create Client

```bash
python -m ae.cli create-client \
  --db acq.db \
  --client-id demo1 \
  --name "Demo Plumbing" \
  --trade plumber \
  --city brisbane \
  --country au \
  --phone "+61-400-000-000" \
  --email "leads@example.com" \
  --service-area "Brisbane North"
```

### 4. Create Page

```bash
python -m ae.cli create-page \
  --db acq.db \
  --page-id p1 \
  --client-id demo1 \
  --template-id trade_lp \
  --slug demo-plumbing-v1 \
  --url https://yourdomain.com/au/plumber-brisbane/demo-plumbing-v1
```

### 5. Setup Chat Channel

Chat channels are created via Python API or console. Example:

```python
from ae import repo
from ae.enums import ChatProvider

repo.upsert_chat_channel(
    db_path="acq.db",
    channel_id="ch_demo_whatsapp",
    provider=ChatProvider.whatsapp,
    handle="+61-400-000-000",
    display_name="Demo Plumbing WhatsApp",
    meta_json={"client_id": "demo1"},
)
```

Or via console API: `POST /api/chat-channels`

### 6. Setup Menu

Menus are created via console API:

```bash
curl -X POST http://localhost:8000/api/menus?db=acq.db \
  -H "Content-Type: application/json" \
  -d '{
    "menu_id": "menu_demo1",
    "client_id": "demo1",
    "name": "Demo Plumbing Services",
    "language": "en",
    "currency": "AUD",
    "status": "draft",
    "meta": {"public_url": "https://yourdomain.com/menu-demo1.html"}
  }'
```

### 7. Generate QR Code

QR codes can be generated via console API:

```bash
curl -X POST http://localhost:8000/api/menus/menu_demo1/qr?db=acq.db \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://yourdomain.com/menu-demo1.html",
    "output_dir": "generated/qr",
    "enable_attribution": true
  }'
```

### 8. Test Ads Integration

Ads adapters (Meta/Google stubs) are tested programmatically:

```python
from ae.ads import get_ads_adapter

meta = get_ads_adapter("meta")
spend = meta.pull_spend(client_id="demo1", date_from="2026-01-01", date_to="2026-01-07")
```

### 9. Validate Page

```bash
python -m ae.cli validate-page --db acq.db --page-id p1
```

### 10. Publish Page (Optional)

```bash
python -m ae.cli publish-page --db acq.db --page-id p1
```

### 11. Create Admin User

```bash
# Set database path
export AE_DB_PATH=$(pwd)/acq.db  # Linux/macOS
# or
set AE_DB_PATH=acq.db  # Windows

# Create admin user
# Windows:
set PYTHONPATH=src
ops\scripts\ae_cli.bat auth-create-user --username admin --role admin

# Linux/macOS:
export PYTHONPATH=src
bash ops/scripts/ae_cli.sh auth-create-user --username admin --role admin

# Set password (will prompt)
# Windows:
ops\scripts\ae_cli.bat auth-set-password --username admin

# Linux/macOS:
bash ops/scripts/ae_cli.sh auth-set-password --username admin
```

### 12. Run Tests

```bash
# Unit tests
pytest -v

# Compliance checks
python ops/checks/run_all.py
```

### 13. Start Console

```bash
# Set database path
export AE_DB_PATH=$(pwd)/acq.db  # Linux/macOS
set AE_DB_PATH=acq.db  # Windows

# Start console
python -m ae.cli serve-console --host 0.0.0.0 --port 8000
```

### 14. Run Smoke Tests

In another terminal:

```bash
# Set base URLs
export BASE_PUBLIC=http://localhost:8001
export BASE_CONSOLE=http://localhost:8000

# Run smoke tests
bash ops/smoke_test.sh
```

## Verification Checklist

After initialization, verify:

- [ ] Database file exists and is not empty
- [ ] Template `trade_lp` exists
- [ ] Client `demo1` exists
- [ ] Page `p1` exists
- [ ] Chat channel `ch_demo_whatsapp` exists
- [ ] Menu `menu_demo1` exists with sections and items
- [ ] QR code generated in `generated/qr/`
- [ ] Ads adapters (Meta/Google) work
- [ ] Admin user `admin` exists
- [ ] Console starts without errors
- [ ] Health endpoint responds: `curl http://localhost:8000/health`
- [ ] Unit tests pass
- [ ] Compliance checks pass

## Troubleshooting

### Database Already Exists

If the database already exists, the script will initialize it anyway (safe operation).

### Tests Fail

If unit tests fail:
1. Check Python version: `python --version` (needs 3.10+)
2. Verify dependencies: `pip list | grep pydantic`
3. Check database path is correct
4. Review test output for specific errors

### Console Won't Start

1. Check if port 8000 is available: `netstat -an | grep 8000`
2. Verify `AE_DB_PATH` environment variable is set
3. Check console logs for errors

### Admin User Creation Fails

If admin user already exists, this is OK - the script handles it gracefully.

## Next Steps After Initialization

1. **Configure Environment**:
   - Copy `.env.example` to `.env`
   - Set `AE_CONSOLE_SECRET` for production
   - Configure other environment variables as needed

2. **Set Admin Password**:
   ```bash
   python -m ae.cli auth-set-password --username admin
   ```

3. **Access Console**:
   - Open: http://localhost:8000/console (or http://localhost:8000/ which redirects to /console)
   - Login with admin credentials
   - **Note**: The root path `/` redirects to `/console` automatically

4. **Configure Client Onboarding**:
   - Follow `docs/CLIENT_ONBOARDING_V1.md`
   - Set up UTM policies
   - Configure event tracking

5. **Test Lead Intake**:
   ```bash
   curl -X POST http://localhost:8001/lead \
     -H "Content-Type: application/json" \
     -d '{"name":"Test","email":"test@example.com","message":"hello","utm":{"utm_source":"test"}}'
   ```

6. **Review Operations Docs**:
   - `ops/DEPLOYMENT.md` - Deployment guide
   - `ops/BACKUP_POLICY.md` - Backup procedures
   - `ops/OBSERVABILITY.md` - Monitoring setup

## Production Readiness

Before launching to production:

- [ ] All tests pass
- [ ] Database backups configured
- [ ] Environment variables set
- [ ] Admin password changed
- [ ] Console secret set
- [ ] Rate limiting configured
- [ ] Monitoring/logging configured
- [ ] Backup scripts tested
- [ ] Deployment checklist reviewed (`ops/DEPLOYMENT_READINESS.md`)

## Support

For issues or questions:
- Review `README.md` for general information
- Check `ops/DEPLOYMENT.md` for deployment details
- Review test output for specific error messages
