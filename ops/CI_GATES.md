# CI Gates

This repo uses a small set of “gates” to prevent release drift.

## What gates check
- Version SSOT consistency:
  - `ops/VERSION.txt`
  - `pyproject.toml`
  - `src/ae/__init__.py` (`__version__`)
- Changelog section exists for current version and does not contain empty bullet placeholders.
- Log horizon has an entry that mentions the current version.

## Run locally
```bash
pytest -q
python ops/ci_release_gates.py
```

## In CI
See `.github/workflows/ci.yml`.
