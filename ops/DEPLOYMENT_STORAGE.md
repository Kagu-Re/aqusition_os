# Storage & Deployment Notes

## Current store
The engine currently uses **SQLite**.

## Recommended config
Prefer `AE_DB_URL` so the config surface stays stable when you later switch to a managed DB.

### Examples
- Local relative file:
  - `AE_DB_URL=sqlite://data/acq.db`

- Absolute path:
  - `AE_DB_URL=sqlite:////var/lib/acq_engine/acq.db`

If `AE_DB_URL` is not set, the system falls back to:
- `AE_DB_PATH` (legacy), then
- `data/acq.db`

## Roadmap
A future patch will add Postgres support behind the same interface (`Storage`), without touching business logic.
