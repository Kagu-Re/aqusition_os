# Release Checklist

Use this as a repeatable sequence. The goal is **clarity + traceability**.

## 0) Decide version
- [ ] Pick `X.Y.Z` using SemVer rules (`ops/RELEASE_RULES.md`)
- [ ] Write 1–2 sentences: “Why this release exists” (paste into changelog)

## 1) Pre-flight
- [ ] CI gates pass (run `python ops/ci_release_gates.py`)

- [ ] `pytest -q` passes
- [ ] `ruff` / `mypy` (if enabled) passes
- [ ] `ops/smoke_test.sh` passes (if docker/services are running)

## 2) Update version surfaces (SSOT)
- [ ] `ops/VERSION.txt`
- [ ] `pyproject.toml`
- [ ] `src/ae/__init__.py`

## 3) Changelog
- [ ] Add section `## [X.Y.Z] - YYYY-MM-DD` under `[Unreleased]`
- [ ] Include: Added/Changed/Fixed (at minimum)
- [ ] Add migration notes if breaking

## 4) Docs & runbooks
- [ ] Runbooks updated if commands/config changed
- [ ] Config reference updated if env vars changed

## 5) Build artifact
- [ ] Create `acq_engine_vX_Y_Z.zip`
- [ ] Verify zip contents include:
  - `CHANGELOG.md`
  - `ops/*` runbooks/docs
  - `src/*` code
  - `tests/*`

## 6) Release log horizon
- [ ] Append a short entry in `ops/LOG_HORIZON.md`
- [ ] Mark patch items complete in `ops/PATCH_QUEUE.md`

## 7) Sanity review (2 min)
- [ ] No secrets committed (`.env` excluded; `.env.example` ok)
- [ ] Health endpoints ok (`/health`, `/ready`)
- [ ] Request logs do not include PII (emails, bodies)
