# Naming Convention — demo1

Consistency prevents budget leaks.

## Client
- `client_id`: `demo1`
- `trade`: `plumber`
- `geo`: `brisbane, au`

## Campaign key format
`<client_id>-<trade>-<geo>-<objective>-v<iteration>`

Example:
- `demo1-plumber-brisbane-lead-v1`
- `demo1-plumber-brisbane-search-v1`

## Asset IDs
- creative: `cr_<format>_<angle>_<n>`
- landing sections: `sec_<purpose>_<n>`

## Guardrails
- Don’t reuse IDs for different meanings.
- If you change offer angle, bump iteration.
