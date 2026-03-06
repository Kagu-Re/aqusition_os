# Backup & Restore Policy

Goal: make deployments **recoverable** with minimal operator effort.

## What we back up
- Persistent data volume (default Docker volume: `ae_data`)
- Any local config you treat as state (usually **not** `.env`, but secrets should be managed separately)

## Recommended cadence
- **Daily** backup for active deployments
- **Before** any migration / schema change
- **Before** upgrading to a new major version

## Retention
Default script keeps **14** most recent backups.

## Commands
### Backup (Docker volume)
```bash
./ops/scripts/backup.sh docker ./backups
./ops/scripts/rotate_backups.sh ./backups 14
```

### Restore (Docker volume)
> WARNING: this wipes the current volume before restore.
```bash
./ops/scripts/restore.sh docker ./backups/ae_backup_YYYYmmdd_HHMMSS.tar.gz
```

### Backup/restore (path-based)
Use this if you mount a host directory instead of a named volume.
```bash
./ops/scripts/backup.sh path ./data ./backups
./ops/scripts/restore.sh path ./backups/ae_backup_....tar.gz ./data
```

## Operational notes
- Test restore quarterly (or at least once per environment)
- Keep backups off-host (S3, Drive, etc.) for real resilience
