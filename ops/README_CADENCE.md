# Cadence Enforcement (v0.1.2)

A release is valid only if:
1) Patch metadata exists (`ops/patches/P-YYYYMMDD-####.json`)
2) Tests pass
3) Log Horizon entry appended (append-only)
4) Release record written (`ops/releases/P-YYYYMMDD-####.json`)

## CLI
Create patch:
```bash
python -m ae.cli create-patch --patch-id P-20260130-0003 --version v0.1.2 --type patch --summary "Cadence enforcer + auto log"
```

Verify release (runs tests, appends log entry, writes release record):
```bash
python -m ae.cli verify-release --patch-id P-20260130-0003 --log-horizon-md ops/LOG_HORIZON.md --artifact acq_engine_v0_1_2.zip --notes "..." --next "..."
```

## MCP
`ae.mcp_server` also exposes:
- cadence.create_patch
- cadence.verify_release


## Convenience commands (v0.1.3)

Auto-generate the next patch id and create patch meta:
```bash
python -m ae.cli start-work --version v0.1.3 --type patch --summary "Auto patch id + start/finish work"
```

Finish work (runs tests, appends log entry, writes release record):
```bash
python -m ae.cli finish-work --patch-id P-YYYYMMDD-#### --log-horizon-md ops/LOG_HORIZON.md --artifact acq_engine_v0_1_3.zip --notes "..." --next "..."
```

You can also print the next patch id:
```bash
python -m ae.cli next-patch-id
```
