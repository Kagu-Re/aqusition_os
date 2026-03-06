# Release Meta

Purpose: allow CI to enforce **artifact presence** OR a **documented skip reason**.

## File
Create `ops/release_meta.json` (not the `.example`) with:

```json
{
  "version": "3.2.0",
  "artifact": {
    "mode": "file",
    "filename": "acq_engine_v3_2_0.zip",
    "reason": ""
  }
}
```

### Modes
- `mode: "file"` → CI expects `filename` to exist at repo root.
- `mode: "skip"` → CI expects a non-empty `reason` explaining why artifact isn't present.

## Why this exists
Some repos don't commit zip artifacts. This provides a formal “escape hatch” while staying explicit.

## Environment policy
You may optionally set:

```json
{
  "env": "dev" | "prod"
}
```

- `env: "dev"` (default) → `artifact.mode` may be `file` or `skip`
- `env: "prod"` → `artifact.mode` **must** be `file`

This lets CI prevent “skip” releases for production.
