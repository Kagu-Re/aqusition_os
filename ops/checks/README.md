# ops/checks

One-liner local compliance checks for the project.

## Run everything
```bash
python ops/checks/run_all.py
```

## Use a custom alias registry
```bash
python ops/checks/run_all.py --aliases-path cfg/aliases.json
```

This currently runs:
- `ae.cli validate-aliases`
- `pytest -q`

- `smoke.py` is for deployment smoke tests against a running server.
