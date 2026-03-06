# CLI Operations Guide

## Overview

Yes, I can operate the system using CLI commands! This document demonstrates the available CLI operations and how to use them.

## Available CLI Commands

### Database & Setup
- `init-db` - Initialize SQLite schema
- `migrate-workqueue` - Migrate WORK_QUEUE.md to latest schema

### Client Management
- `create-client` - Create a new client
- `generate-onboarding` - Generate onboarding pack for a client
- `onboarding-init` - Initialize onboarding templates

### Template Management
- `create-template` - Create a new template

### Page Management
- `create-page` - Create a new landing page
- `validate-page` - Validate a page
- `publish-page` - Publish a page
- `pause-page` - Pause a page
- `bulk-validate` - Validate multiple pages
- `bulk-pause` - Pause multiple pages
- `bulk-publish` - Publish multiple pages
- `bulk-run` - Generic bulk operations (validate|pause|publish)

### Ads & Analytics
- `ads-simulate` - Simulate ads platform pulls
- `ads-pull-stats` - Pull ads stats and write to database
- `record-ad-stat` - Record a single ad stat
- `import-ad-stats-csv` - Import ad stats from CSV
- `import-meta-export-csv` - Import Meta ads export CSV
- `import-google-ads-export-csv` - Import Google Ads export CSV
- `validate-aliases` - Validate ad platform aliases

### Reporting & KPIs
- `kpi-report` - Generate KPI report
- `kpi-client-report` - Generate KPI report per client
- `export-kpis` - Export KPIs to CSV
- `analytics-summary` - Analytics summary
- `diagnostics-client` - Run diagnostics for a client
- `guardrails-evaluate` - Evaluate budget guardrails
- `guardrails-autoplan` - Generate action checklist from guardrails

### Work Management
- `enqueue-work` - Enqueue a work item
- `list-work` - List work items
- `record-event` - Record an event
- `enqueue-bulk` - Enqueue bulk work
- `run-bulk` - Run bulk work

### Patch Management
- `create-patch` - Create a patch
- `verify-release` - Verify a release
- `next-patch-id` - Get next patch ID
- `start-work` - Start work on a patch
- `finish-work` - Finish work on a patch

### Operations
- `ops-run` - Run operations workflow
- `client-status` - Get client operational status
- `work-backfill-client-ids` - Backfill missing client IDs

### Console
- `serve-console` - Start the web console server

## Usage Examples

### Setting Up Environment

**Windows PowerShell:**
```powershell
$env:PYTHONPATH='src'
```

**Windows CMD:**
```cmd
set PYTHONPATH=src
```

**Linux/macOS:**
```bash
export PYTHONPATH=src
```

### Client Operations

**Create a client:**
```bash
python -m ae.cli create-client \
  --db acq.db \
  --client-id plumber-cm-oldtown \
  --name "CM Oldtown Plumbing" \
  --trade plumber \
  --city "chiang mai" \
  --phone "+66-80-000-0000" \
  --email "leads@example.com" \
  --service-area "Chiang Mai Old Town"
```

**Initialize onboarding templates:**
```bash
python -m ae.cli onboarding-init --db acq.db --client-id plumber-cm-oldtown
```

**Generate onboarding pack:**
```bash
python -m ae.cli generate-onboarding \
  --db acq.db \
  --client-id plumber-cm-oldtown \
  --out-root clients
```

### Page Operations

**Create a page:**
```bash
python -m ae.cli create-page \
  --db acq.db \
  --page-id p-plumber-cm-v1 \
  --client-id plumber-cm-oldtown \
  --template-id trade_lp \
  --slug plumber-cm-oldtown-v1 \
  --url https://yourdomain.com/th/plumber/chiang-mai/plumber-cm-oldtown-v1
```

**Validate a page:**
```bash
python -m ae.cli validate-page --db acq.db --page-id p-plumber-cm-v1
```

**Publish a page:**
```bash
python -m ae.cli publish-page --db acq.db --page-id p-plumber-cm-v1
```

**Bulk operations:**
```bash
# Validate all draft pages for a client
python -m ae.cli bulk-run \
  --action validate \
  --db acq.db \
  --client-id plumber-cm-oldtown \
  --page-status draft

# Publish all validated pages
python -m ae.cli bulk-run \
  --action publish \
  --db acq.db \
  --client-id plumber-cm-oldtown \
  --page-status draft \
  --execute
```

### Reporting Operations

**Generate KPI report:**
```bash
python -m ae.cli kpi-client-report \
  --db acq.db \
  --client-id plumber-cm-oldtown \
  --platform meta \
  --window 7d \
  --fmt markdown
```

**Run diagnostics:**
```bash
python -m ae.cli diagnostics-client \
  --db acq.db \
  --client-id plumber-cm-oldtown \
  --platform meta \
  --since-iso 2024-01-01T00:00:00Z
```

**Evaluate guardrails:**
```bash
python -m ae.cli guardrails-evaluate \
  --db acq.db \
  --client-id plumber-cm-oldtown \
  --platform meta
```

### Work Operations

**List work items:**
```bash
python -m ae.cli list-work --db acq.db --status new
```

**Record an event:**
```bash
python -m ae.cli record-event \
  --db acq.db \
  --page-id p-plumber-cm-v1 \
  --event-name page_view \
  --params-json '{"source":"google","medium":"cpc"}'
```

### Console Server

**Start console:**
```bash
python -m ae.cli serve-console --host 127.0.0.1 --port 8000
```

Then access at: `http://localhost:8000/console`

## Python API Alternative

You can also use the Python API directly:

```python
from ae import repo
from ae.models import Client
from ae.enums import Trade

# List clients
clients = repo.list_clients('acq.db')
for c in clients:
    print(f"{c.client_id}: {c.client_name}")

# Get client
client = repo.get_client('acq.db', client_id='plumber-cm-oldtown')

# Initialize onboarding templates
templates = repo.ensure_default_onboarding_templates('acq.db', 'plumber-cm-oldtown')

# Generate onboarding pack
from ae.onboarding import generate_onboarding_pack
files = generate_onboarding_pack(client, out_root='clients')
```

## What I Can Do

As an AI assistant, I can:

1. **Execute CLI commands** - Run any CLI command on your behalf
2. **Query the database** - Use Python API to read data
3. **Create/modify entities** - Create clients, pages, templates, etc.
4. **Generate reports** - Run KPI reports, diagnostics, guardrails
5. **Bulk operations** - Validate, publish, or pause multiple pages
6. **Workflow automation** - Run end-to-end operations

## Example: Complete Workflow

Here's an example of a complete workflow I can execute:

```bash
# 1. Create client
python -m ae.cli create-client \
  --db acq.db \
  --client-id plumber-cm-oldtown \
  --name "CM Oldtown Plumbing" \
  --trade plumber \
  --city "chiang mai" \
  --phone "+66-80-000-0000" \
  --email "leads@example.com" \
  --service-area "Chiang Mai Old Town"

# 2. Initialize onboarding
python -m ae.cli onboarding-init --db acq.db --client-id plumber-cm-oldtown

# 3. Generate onboarding pack
python -m ae.cli generate-onboarding \
  --db acq.db \
  --client-id plumber-cm-oldtown \
  --out-root clients

# 4. Create template (if needed)
python -m ae.cli create-template \
  --db acq.db \
  --template-id trade_lp \
  --version 1.0.0 \
  --cms-schema 1.0 \
  --events 1.0

# 5. Create page
python -m ae.cli create-page \
  --db acq.db \
  --page-id p-plumber-cm-v1 \
  --client-id plumber-cm-oldtown \
  --template-id trade_lp \
  --slug plumber-cm-oldtown-v1 \
  --url https://yourdomain.com/th/plumber/chiang-mai/plumber-cm-oldtown-v1

# 6. Validate page
python -m ae.cli validate-page --db acq.db --page-id p-plumber-cm-v1

# 7. Publish page
python -m ae.cli publish-page --db acq.db --page-id p-plumber-cm-v1

# 8. Generate KPI report
python -m ae.cli kpi-client-report \
  --db acq.db \
  --client-id plumber-cm-oldtown \
  --window 7d \
  --fmt markdown
```

## Notes

- Always set `PYTHONPATH=src` before running CLI commands (or use wrapper scripts)
- Database path defaults to `acq.db` in the current directory
- Most commands support `--help` for detailed usage
- Bulk operations support `--execute` flag (default is dry-run)
- Console server requires authentication (X-AE-SECRET header or login)

## Wrapper Scripts

For convenience, wrapper scripts are available:
- Windows: `ops/scripts/ae_cli.bat`
- Linux/macOS: `ops/scripts/ae_cli.sh`

These handle PYTHONPATH automatically.
