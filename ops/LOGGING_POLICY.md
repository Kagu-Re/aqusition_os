# Logging policy

Goal: keep logs useful for operations without leaking personal data or secrets.

## Principles
- Do not log request/response bodies.
- Do not log raw IP addresses unless explicitly required.
- Prefer structured logs (JSON) and redact at source.

## Controls (env)
- `AE_LOG_MAX_CHARS` (default 600): hard cap on any single logged string.
- `AE_LOG_CLIENT_IP` (default 0): if enabled, logs only a coarse IPv4 hint.
- `AE_AUDIT_LOG` (default 1): audit records for operator actions (no payloads).

## Redaction
`ae.log_safety.sanitize_text()` masks:
- email addresses
- phone-like sequences
- long token-like strings (API keys/bearer tokens)

## Retention
Recommended defaults:
- Public deployments: 7–14 days retention
- Internal / dev: 3–7 days

If you ship logs to a vendor (e.g., Loki/ELK/CloudWatch):
- enforce TTL there
- restrict access
- document who can view logs

## Verification
- Unit tests cover common redaction cases.
- Do not add new logging that includes user-provided free-text without `sanitize_text`.
