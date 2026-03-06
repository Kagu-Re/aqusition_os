# Initialization and Testing Scripts

This directory contains scripts for system initialization and testing.

## e2e_init_and_test.py

Comprehensive end-to-end initialization and testing script.

**Usage:**
```bash
# Full initialization and testing
python ops/scripts/e2e_init_and_test.py

# Custom database path
python ops/scripts/e2e_init_and_test.py --db-path /path/to/acq.db

# Skip tests (faster setup)
python ops/scripts/e2e_init_and_test.py --skip-tests

# Skip console and smoke tests
python ops/scripts/e2e_init_and_test.py --skip-console --skip-smoke
```

**What it does:**
1. Checks prerequisites (Python version, dependencies)
2. Initializes database schema
3. Creates demo data (template, client, page)
4. Validates page
5. Tests publishing
6. Creates admin user
7. Runs unit tests
8. Runs compliance checks
9. Tests console startup
10. Runs smoke tests (if console running)

**Output:**
- Color-coded progress indicators
- Detailed error messages
- Summary report at the end

See `docs/E2E_INITIALIZATION.md` for detailed documentation.

## Other Scripts

- `backup.sh` - Database backup utility
- `restore.sh` - Database restore utility
- `rotate_backups.sh` - Backup rotation
- `run_docker.sh` - Docker Compose helper
- `run_proxy.sh` - Reverse proxy helper
- `stop_docker.sh` - Stop Docker services
