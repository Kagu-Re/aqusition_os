# System Validation Guide

This guide explains how to validate system functionality comprehensively without requiring full deployment.

## Overview

The validation system is organized into **phases** that can run independently or together. Most phases can run **without deployment**, allowing you to validate functionality incrementally.

## Quick Start

### Run All Phases (No Deployment Required)

```bash
# Run phases 0-3 and 6 (skips deployment phases 4-5)
python ops/scripts/validate_system.py --all

# Run all phases including deployment (requires services running)
python ops/scripts/validate_system.py --all --include-deployment
```

### Run Specific Phase

```bash
# Run Phase 1: Core Functionality
python ops/scripts/validate_system.py --phase 1

# Run Phase 2: File System
python ops/scripts/validate_system.py --phase 2
```

### JSON Output

```bash
# Get JSON output for CI/CD integration
python ops/scripts/validate_system.py --all --json
```

## Validation Phases

### Phase 0: Prerequisites

**Deployment Required**: No

**What it validates**:
- Python version (3.10+)
- Required dependencies installed (pydantic, fastapi, typer)

**Example**:
```bash
python ops/scripts/validate_system.py --phase 0
```

**Common Issues**:
- Missing dependencies: Run `pip install -r requirements.txt`
- Wrong Python version: Use Python 3.10 or higher

---

### Phase 1: Core Functionality

**Deployment Required**: No

**What it validates**:
- Database schema and integrity
- Data quality (completeness, relationships)
- Cross-component consistency (events-leads, UTM consistency, timeline)
- State machine transitions

**Example**:
```bash
python ops/scripts/validate_system.py --phase 1 --db-path acq.db
```

**What gets checked**:
- Database file exists and is accessible
- Required tables exist
- Database integrity (referential integrity, orphaned records)
- Data quality (incomplete clients, duplicate slugs)
- Cross-component consistency (events without leads, timeline mismatches)
- State machine validity

**Common Issues**:
- Database not found: Create database with `python -m ae.cli init-db --db acq.db`
- Integrity issues: Review integrity report for specific problems
- Missing relationships: Check for orphaned pages, clients, templates

---

### Phase 2: File System

**Deployment Required**: No

**What it validates**:
- Published HTML files exist
- HTML structure is valid
- Tracking JavaScript is present and correctly configured
- Page IDs match expected values
- API endpoints are configured correctly

**Example**:
```bash
python ops/scripts/validate_system.py --phase 2
```

**What gets checked**:
- HTML files exist in `exports/static_site/`
- Files are not empty
- Valid HTML doctype
- Tracking JavaScript embedded
- PAGE_ID configured correctly
- API endpoint (`/v1/event`) present
- UTM parameter extraction code present
- Event handlers configured (call_click, quote_submit, thank_you_view)
- CSS/assets referenced correctly

**Common Issues**:
- No published files: Publish a page first with `python -m ae.cli publish-page --db acq.db --page-id p1`
- Missing tracking code: Re-publish the page
- Incorrect PAGE_ID: Check page configuration

---

### Phase 3: API Contracts

**Deployment Required**: No

**What it validates**:
- Event schemas are properly registered
- Schema registry is valid
- Event payload structures are correct
- Required fields are present

**Example**:
```bash
python ops/scripts/validate_system.py --phase 3
```

**What gets checked**:
- Event registry loaded with valid event types
- Event schema structure (topic format, schema version, required keys)
- Schema registry validation
- Sample event payload validation

**Common Issues**:
- Empty registry: Check `src/ae/op_event_registry.py`
- Invalid schemas: Review schema definitions

---

### Phase 4: Integration

**Deployment Required**: Yes (local services)

**What it validates**:
- Console health endpoint responds
- Public API health endpoint responds
- Services are accessible

**Example**:
```bash
# Start services first
docker compose up --build

# Then run validation
python ops/scripts/validate_system.py --phase 4
```

**What gets checked**:
- Console health endpoint (`http://localhost:8000/health`)
- Public API health endpoint (`http://localhost:8001/health`)

**Common Issues**:
- Services not running: Start with `docker compose up` or `python -m ae.cli serve-console`
- Wrong URLs: Use `--console-url` and `--public-url` flags

---

### Phase 5: Deployment

**Deployment Required**: Yes (full deployment)

**What it validates**:
- Production environment variables set
- CORS configuration is restrictive
- Security settings are configured

**Example**:
```bash
python ops/scripts/validate_system.py --phase 5
```

**What gets checked**:
- `AE_ENV` environment variable
- `AE_CONSOLE_SECRET` environment variable
- `AE_PUBLIC_CORS_ORIGINS` configuration (should not be `*` in production)

**Common Issues**:
- Missing environment variables: Set required vars in `.env` file
- CORS too permissive: Restrict `AE_PUBLIC_CORS_ORIGINS` to your domain(s)

---

### Phase 6: Business Rules

**Deployment Required**: No

**What it validates**:
- Publish readiness for pages
- Onboarding policy compliance
- Template version compatibility
- Event map completeness

**Example**:
```bash
python ops/scripts/validate_system.py --phase 6 --db-path acq.db
```

**What gets checked**:
- Page publish readiness (client, template, events)
- Template version compatibility
- Required events validated
- Page URL and slug format
- Onboarding directory structure
- UTM policy file exists
- Naming convention file exists
- Event map file exists and includes required events

**Common Issues**:
- Pages not ready: Fix missing client fields, validate events
- Missing onboarding files: Create onboarding directory structure
- Incomplete event map: Add required events to event map

---

## Usage Examples

### Validate Before Deployment

```bash
# Run all non-deployment phases
python ops/scripts/validate_system.py --all

# This runs phases 0, 1, 2, 3, and 6
# Validates ~80% of functionality without deployment
```

### Validate After Local Services Start

```bash
# Start services
docker compose up --build

# Run all phases including integration
python ops/scripts/validate_system.py --all --include-deployment
```

### Validate Specific Component

```bash
# Validate only database
python ops/scripts/validate_system.py --phase 1

# Validate only published files
python ops/scripts/validate_system.py --phase 2

# Validate only business rules
python ops/scripts/validate_system.py --phase 6
```

### CI/CD Integration

```bash
# Get JSON output for CI/CD
python ops/scripts/validate_system.py --all --json > validation_results.json

# Check exit code
python ops/scripts/validate_system.py --all
echo $?  # 0 = passed, 1 = failed
```

## Troubleshooting

### "Database file not found"

**Solution**: Create database first:
```bash
python -m ae.cli init-db --db acq.db
```

### "No published HTML files found"

**Solution**: Publish a page first:
```bash
python -m ae.cli publish-page --db acq.db --page-id p1
```

### "Console not running" (Phase 4)

**Solution**: Start services:
```bash
docker compose up --build
# Or
python -m ae.cli serve-console
```

### "Module not found" errors

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### Integrity check failures

**Solution**: Review integrity report:
```bash
python -m ae.cli integrity-check --db acq.db
```

## Integration with Existing Scripts

The validation system complements existing scripts:

- **`ops/scripts/e2e_init_and_test.py`**: Full initialization and testing
- **`ops/checks/run_all.py`**: Compliance checks (aliases + pytest)
- **`ops/smoke_test.sh`**: Smoke tests for running services

**Recommended workflow**:
1. Run `validate_system.py --all` (phases 0-3, 6) - no deployment needed
2. Start services and run `smoke_test.sh` - validates APIs
3. Run `e2e_init_and_test.py` - full initialization

## Output Format

### Console Output

```
[Phase 1/7] Core Functionality: Database, models, business logic
  ✓ database_exists: Database file exists: acq.db
  ✓ database_accessible: Database is accessible
  ✓ table_clients: Table 'clients' exists
  ...

Validation Summary
============================================================
Total phases: 7
Passed: 6
Failed: 1
Warnings: 2
Errors: 0
```

### JSON Output

```json
{
  "timestamp": "2026-02-06T12:00:00Z",
  "phases": {
    "phase_0": {
      "status": "passed",
      "name": "Prerequisites",
      "checks": 4,
      "errors": 0,
      "warnings": 0,
      "details": [...]
    },
    ...
  },
  "summary": {
    "total_phases": 7,
    "passed": 6,
    "failed": 1,
    "warnings": 2,
    "errors": 0
  }
}
```

## Best Practices

1. **Run validation before deployment**: Use `--all` (without `--include-deployment`) to validate most functionality
2. **Fix issues incrementally**: Address failures phase by phase
3. **Use JSON output for CI/CD**: Integrate validation into your CI pipeline
4. **Validate after changes**: Run validation after code changes or configuration updates
5. **Check warnings**: Warnings indicate potential issues that should be reviewed

## Next Steps

After validation passes:
1. Start services: `docker compose up --build`
2. Run smoke tests: `./ops/smoke_test.sh`
3. Test manually: Open console UI and test functionality
4. Deploy to production: Follow deployment guide

## Related Documentation

- [E2E Initialization Guide](E2E_INITIALIZATION.md)
- [Publishing Walkthrough](PUBLISHING_WALKTHROUGH.md)
- [Deployment Guide](../ops/DEPLOYMENT_GUIDE.md)
- [How Event Tracking Works](HOW_EVENT_TRACKING_WORKS.md)
