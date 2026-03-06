# Release Rules

## SemVer
We use **Semantic Versioning**: `MAJOR.MINOR.PATCH`

- **MAJOR**: breaking API/behavior changes
- **MINOR**: new features, backward compatible
- **PATCH**: bugfixes, backward compatible

## Artifact naming
Release artifacts must follow a single stable convention:

- `acq_engine_vX_Y_Z.zip`

Examples:
- `acq_engine_v2_9_0.zip`
- `acq_engine_v3_0_0.zip`

## Version single source of truth (SSOT)
A release must update all version surfaces:

- `ops/VERSION.txt`
- `pyproject.toml` (Poetry version)
- `src/ae/__init__.py` (`__version__`)

## Changelog policy
- Every release **must** add a section to `CHANGELOG.md`.
- Sections should list *Added / Changed / Fixed / Removed / Security*.
- Keep entries human-readable. No raw commit dumps.

## Compatibility policy
If you introduce a breaking change:
- bump MAJOR,
- write a “Migration” note in the changelog,
- update runbooks/examples that would break.
