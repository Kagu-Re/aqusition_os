# Risk Register

Updated: 2026-02-03

| Risk ID | Area | Risk | Impact | Likelihood | Mitigation | Status |
|---|---|---|---|---|---|---|
| R-0001 | Versioning | Version drift between pyproject / runtime / ops | Mis-deploy + hard rollbacks | Medium | SSOT: pyproject + health version check | ✅ mitigated v1.3.4 |
| R-0002 | Data | DB artifacts committed (e.g. *.db) | Data leakage | High | .gitignore + remove db from repo | ✅ mitigated v1.3.4 |
| R-0003 | Security | Cookie not Secure in HTTPS deployments | Session theft over non-HTTPS or mixed env | Medium | AE_COOKIE_SECURE=1 behind HTTPS | ✅ mitigated v1.3.4 |
| R-0004 | Security | Cookie SameSite too permissive / CSRF | CSRF-like abuse | Medium | AE_COOKIE_SAMESITE=strict + CSRF token enforcement for cookie sessions | ✅ mitigated v1.4.0 |
| R-0005 | Maintainability | Large “god files” | Slower patches + regressions | High | Incremental module split w/ tests | ⬜ planned |
| R-0006 | Scaling | SQLite write locks under concurrency | Bulk ops failure | Medium | WAL + busy_timeout + migration path | ⬜ planned |
