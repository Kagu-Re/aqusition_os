# Validation System Quick Start

## Quick Commands

```bash
# Run all non-deployment phases (recommended)
python ops/scripts/validate_system.py --all

# Run specific phase
python ops/scripts/validate_system.py --phase 1

# JSON output for CI/CD
python ops/scripts/validate_system.py --all --json

# Include deployment phases (requires services running)
python ops/scripts/validate_system.py --all --include-deployment
```

## Phase Overview

- **Phase 0**: Prerequisites (Python, dependencies)
- **Phase 1**: Core Functionality (database, data quality, consistency)
- **Phase 2**: File System (published HTML files)
- **Phase 3**: API Contracts (schemas, payloads)
- **Phase 4**: Integration (requires services running)
- **Phase 5**: Deployment (requires full deployment)
- **Phase 6**: Business Rules (onboarding, publish readiness)

## Typical Workflow

1. **Before deployment**: Run `--all` (skips phases 4-5)
2. **After starting services**: Run `--all --include-deployment`
3. **CI/CD**: Use `--all --json` for automated testing

## Exit Codes

- `0`: All checks passed
- `1`: One or more checks failed

## See Also

- Full documentation: `docs/VALIDATION_GUIDE.md`
- Existing scripts: `ops/scripts/e2e_init_and_test.py`
