# Acquisition Engine v1 (Local Control Plane)

This project implements the **control plane** for your Acquisition Engine Platform:
- registries (clients/templates/pages/assets)
- policies (publish readiness gates, slug rules)
- queue (work items)
- append-only logs (publish/change/event sanity)
- a CLI for gradual operation
- unit tests

> Note: `SQLModel` isn't available in this execution environment, so v1 uses **Pydantic models + sqlite3** with strict validation.
You can later swap the storage layer to SQLModel/SQLAlchemy without changing your domain policies.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt

# Set PYTHONPATH to include src/ directory
# Windows:
set PYTHONPATH=src
# Linux/macOS:
export PYTHONPATH=src

# Or use wrapper scripts:
# Windows: ops\scripts\ae_cli.bat init-db --db acq.db
# Linux/macOS: bash ops/scripts/ae_cli.sh init-db --db acq.db

python -m ae.cli init-db --db acq.db
python -m ae.cli create-template --db acq.db --template-id trade_lp --version 1.0.0 --cms-schema 1.0 --events 1.0
python -m ae.cli create-client --db acq.db --client-id demo1 --name "Demo Plumbing" --trade plumber --city brisbane --phone "+61-400-000-000" --email "leads@example.com" --service-area "Brisbane North"
python -m ae.cli create-page --db acq.db --page-id p1 --client-id demo1 --template-id trade_lp --slug demo-plumbing-v1 --url https://yourdomain.com/au/plumber-brisbane/demo-plumbing-v1
python -m ae.cli validate-page --db acq.db --page-id p1
python -m ae.cli publish-page --db acq.db --page-id p1
python -m ae.cli enqueue-work --db acq.db --type report --client-id demo1 --priority normal --acceptance "Weekly report generated"
python -m ae.cli list-work --db acq.db
```

## Concepts

- **Registries**: tables of Clients/Templates/Pages/Assets/Events/Campaign UTMs
- **Policies**: hard gates for publish + tracking invariants
- **Queues**: work items with lifecycle states
- **Logs**: append-only history for publish/change + weekly sanity rollups



## Bulk operations (v0.1.1)

Batch validate/publish/pause for multiple pages. Supports `dry_run` to preview impact.

```bash
python -m ae.cli enqueue-bulk --db acq.db --action publish --mode dry_run --page-id p1 --page-id p2 --notes "weekly publish batch"
python -m ae.cli run-bulk --db acq.db --bulk-id <bulk_id>
```

## MCP server scaffold

`python -m ae.mcp_server --repo <repo_root> --log-horizon-md <path_to_log_md>`

- `ops.run_tests`
- `ops.run_cli` (whitelisted)
- `horizon.append_entry` (append-only)


## Cadence enforcement (v0.1.2)

Adds a release gate that auto-populates an append-only Log Horizon entry and writes release records.

- `ops/patches/` — patch metadata (created via `create-patch`)
- `ops/releases/` — release records (created via `verify-release`)
- `ops/LOG_HORIZON.md` — append-only log file (automation target)

See `ops/README_CADENCE.md`.


## Start/finish work helpers (v0.1.3)

- `start-work` creates patch meta, auto-generating the next patch id for today.
- `finish-work` runs tests and (if PASS) appends a Log Horizon entry and writes a release record.


## Adapter layer (v0.2.0)

Adapters isolate external integrations from the control plane.

Default bundle (local simulation):
- Content: `StubContentAdapter` (deterministic payload)
- Publisher: `LocalFilePublisher` (writes `exports/published/<page_id>.json`)
- Analytics: `DbAnalyticsAdapter` (summarizes internal events table)

Example:
```bash
python -m ae.cli publish-page --db acq.db --page-id p1
ls exports/published/p1.json

python -m ae.cli analytics-summary --db acq.db --page-id p1
```


## Adapter selection via config (v0.2.1)

Switch adapter implementations without code changes using env vars:

```bash
# Local file publisher (default)
export AE_PUBLISHER_ADAPTER=tailwind_static
export AE_PUBLISH_OUT_DIR=exports/published

# Framer stub publisher (writes Framer-shaped contract artifacts)
export AE_PUBLISHER_ADAPTER=framer_stub
export AE_FRAMER_OUT_DIR=exports/framer_payloads
```

Publishing with Framer stub produces:
- `exports/framer_payloads/<page_id>.framer.json`


## Publisher contract validation (v0.2.2)

Publisher stub artifacts are validated against versioned schema contracts (Pydantic) before writing.

Currently supported:
- `framer.page_payload.v1`

If validation fails, publish hard-fails and returns schema error messages.


## Tailwind static adapter (v0.3.0)

Publish a static landing page artifact (HTML) using Tailwind utility classes:

```bash
export AE_PUBLISHER_ADAPTER=tailwind_static
export AE_STATIC_OUT_DIR=exports/static_site

python -m ae.cli publish-page --db acq.db --page-id p1
# outputs: exports/static_site/p1/index.html
```

Note: v0.3.0 uses Tailwind CDN for zero-build simulation. Later patch can compile CSS for full offline ownership.


## Full ownership CSS (v0.3.1)

`tailwind_static` no longer uses Tailwind CDN. The exported site includes an owned CSS asset:

- output: `exports/static_site/<page_id>/assets/styles.css`

CSS source-of-truth inside repo:
- `src/ae/assets/tailwind_compiled.css`

To regenerate (requires Node + npm):
```bash
npm install
npm run build:css
```


## CLI

### Ops

- `ae backup-db --db <path>`
- `ae restore-db --db <path> --backup-path <file>`
- `ae ops-health --db <path> [--log]`


### Reconciliation

- `ae reconcile-report` – generates `ops/reports/reconcile_report.md`
- `ae reconcile-apply` – applies reconciliation winners back into BOTH queues (monotonic by default)
- `ae reconcile-queues --apply` – run sync both ways and then apply winners
 adapter overrides (v0.3.2)

Override adapters per command (no env required):

```bash
python -m ae.cli publish-page --db acq.db --page-id p1 \
  --publisher-adapter tailwind_static \
  --static-out-dir exports/static_site
```

Flags:
- `--content-adapter stub`
- `--publisher-adapter local_file|framer_stub|tailwind_static`
- `--analytics-adapter db`
- `--publish-out-dir ...`
- `--framer-out-dir ...`
- `--static-out-dir ...`


## KPI reporting (v0.3.4)

Single page KPI report (uses DB events + optional top-of-funnel placeholders):

```bash
python -m ae.cli kpi-report --db acq.db --page-id p1 --impressions 1000 --clicks 100 --spend 200 --revenue 1000
```

Bulk export (JSON/CSV):

```bash
python -m ae.cli export-kpis --db acq.db --page-status draft --fmt json --out exports/reports/kpis.json
python -m ae.cli export-kpis --db acq.db --page-status draft --fmt csv --out exports/reports/kpis.csv
```


## Webflow publisher stub (v0.3.5)

Writes a Webflow-like CMS payload (no API calls):

```bash
python -m ae.cli publish-page --db acq.db --page-id p1 \
  --publisher-adapter webflow_stub \
  --webflow-out-dir exports/webflow_payloads
```


## Ad stats (v0.3.6)

You can store ad platform aggregates (synthetic or imported) in `ad_stats`.
If `kpi-report` is called **without** placeholders, the analytics layer will fallback to summing `ad_stats`.

Record a stat row:

```bash
python -m ae.cli record-ad-stat --db acq.db --page-id p1 --platform meta --impressions 1000 --clicks 50 --spend 100 --revenue 0
```

KPI report using stored ad stats:

```bash
python -m ae.cli kpi-report --db acq.db --page-id p1
```

Filter by platform or time horizon:

```bash
python -m ae.cli kpi-report --db acq.db --page-id p1 --platform meta --since-iso 2026-01-01T00:00:00
```


## Import ad stats from CSV (v0.3.7)

Normalized CSV columns (case-insensitive):
`page_id, platform, timestamp, impressions, clicks, spend, revenue, campaign_id, adset_id, ad_id`

Import:

```bash
python -m ae.cli import-ad-stats-csv --db acq.db --csv-path exports/ad_stats.csv
```

If your CSV lacks `platform` or `page_id`:

```bash
python -m ae.cli import-ad-stats-csv --db acq.db --csv-path exports/meta_export.csv \
  --default-platform meta --default-page-id p1
```


## Meta/Google export mappers (v0.3.8)

These commands ingest platform exports and map common column names into `ad_stats`.

Meta:
```bash
python -m ae.cli import-meta-export-csv --db acq.db --csv-path exports/meta.csv --page-id p1
```

Google Ads:
```bash
python -m ae.cli import-google-ads-export-csv --db acq.db --csv-path exports/google.csv --page-id p1
```


## Alias registry for ad export headers (v0.3.9)

Header mapping lives in: `ops/ad_platform_aliases.json`

If a client export uses a different header name (e.g. "Cost (USD)" instead of "Cost"),
append the new header string under the right platform + metric key.

Examples:
- `meta.impressions`
- `meta.spend`
- `google.spend`


## Validate alias registry (v0.4.0)

Validate alias config and print coverage:

```bash
python -m ae.cli validate-aliases --aliases-path ops/ad_platform_aliases.json
```

If validation fails, exit code is 2 (useful for CI).


## Local compliance checks (v0.4.1)

One command to run the repo guardrails:

```bash
python ops/checks/run_all.py
```

This runs:
- alias registry validation
- unit tests


## Bulk operations selectors (v0.4.2)

Bulk commands support selectors (in addition to explicit `--page-ids`):

- `--page-status` (draft|live|paused)
- `--client-id`
- `--template-id`
- `--geo-city`
- `--geo-country`
- `--limit`

Examples:

```bash
python -m ae.cli bulk-validate --db acq.db --geo-city brisbane --page-status draft --limit 50
python -m ae.cli bulk-publish --db acq.db --client-id demo1 --execute
python -m ae.cli bulk-pause --db acq.db --template-id trade_lp --execute
```


## Generic bulk runner (v0.4.3)

Instead of remembering multiple bulk commands:

```bash
python -m ae.cli bulk-run --action validate --db acq.db --geo-city brisbane --page-status draft
python -m ae.cli bulk-run --action pause --db acq.db --client-id c1 --execute
python -m ae.cli bulk-run --action publish --db acq.db --template-id trade_lp --execute
```

Actions:
- `validate` (always dry-run)
- `pause` (dry-run unless `--execute`)
- `publish` (dry-run unless `--execute`)


## Scripts

Setup and dev utilities live in `scripts/`. Run from project root:

```bash
python scripts/setup/setup_demo1_client.py
python scripts/runbooks/clear_stale_conversations.py --db acq.db
```

See `scripts/README.md` for the full list. Local dev entry point: `.\start_local_dev.ps1`

## Ops docs (v0.4.4)
- `ops/LOG_HORIZON.md` — append-only horizon log
- `ops/QUEUE.md` — queue summary + completeness %
- `ops/PATCH_QUEUE.md` — patch-level execution queue
- `ops/ASSUMPTION_LEDGER.md` — volatile assumptions + validation plans


## Operator Console (v0.5.1)

Run locally:

```bash
export AE_CONSOLE_SECRET="change-me"
python -m ae.cli serve-console --host 127.0.0.1 --port 8000
```

Open:
- `http://127.0.0.1:8000/console`

Auth:
- If `AE_CONSOLE_SECRET` is set, send `X-AE-SECRET: <secret>` in requests.
  (UI supports `window.AE_SECRET = "<secret>"` in DevTools for quick testing.)


## Console cookie hardening
- `AE_COOKIE_SECURE=1` to set Secure cookies (recommended behind HTTPS)
- `AE_COOKIE_SAMESITE=strict|lax|none` (default: lax)


## Versioning
Single source of truth is `pyproject.toml` (package version). Runtime `/api/health` reports `ae.__version__`.
eve`ops/VERSION.txt` mirrors releases for ops tracking.

## Docker quickstart

```bash
cp .env.example .env
docker compose up --build
```

- Console: http://localhost:8000
- Public API: http://localhost:8001

## Configuration

See `ops/CONFIG_REFERENCE.md` for supported `AE_*` environment variables.

## Releases
- See `CHANGELOG.md`
- Release rules: `ops/RELEASE_RULES.md`
- Release checklist: `ops/RELEASE_CHECKLIST.md`
- Helper: `python ops/release.py X.Y.Z`

## CI
- GitHub Actions workflow: `.github/workflows/ci.yml`
- Release gates: `poetry run python ops/check_release.py --ci`

### Artifact gate
CI expects a release artifact `acq_engine_vX_Y_Z.zip` at repo root, **or** `ops/release_meta.json` with `mode: skip` and a reason.

## Deployment
- See `ops/DEPLOYMENT_GUIDE.md`
- Reverse proxy example: `docker-compose.reverse-proxy.yml`

### Prod release policy
If `ops/release_meta.json` sets `env: "prod"`, CI requires `artifact.mode: "file"` (no skipping).

## Backups
- See `ops/BACKUP_POLICY.md`
- Scripts in `ops/scripts/` (backup/restore/rotate)

## Observability
- Structured logs + metrics: see `ops/OBSERVABILITY.md`

## Logging
- See `ops/LOGGING_POLICY.md`

## Reverse proxy (optional)
For a single entrypoint with console auth, see `ops/PROXY_GUIDE.md`.
Quick run:
- `./ops/scripts/run_proxy.sh`
Proxy URLs:
- Public API: `http://localhost:8080/api/`
- Console: `http://localhost:8080/console`

## Abuse controls
- See `ops/ABUSE_CONTROLS.md`
- Metrics hardening: `ops/METRICS_SECURITY.md`
- Deployment profiles: `ops/DEPLOYMENT_PROFILES.md`
- Logging policy: `ops/LOGGING_POLICY.md`
