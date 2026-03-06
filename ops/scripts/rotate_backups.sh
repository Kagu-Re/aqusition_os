#!/usr/bin/env bash
set -euo pipefail

# Simple backup retention:
# - keep last N backups (default 14)
#
# Usage:
#   ./ops/scripts/rotate_backups.sh ./backups 14

dir="${1:-./backups}"
keep="${2:-14}"

if [[ ! -d "$dir" ]]; then
  echo "No backup dir: $dir (nothing to rotate)"
  exit 0
fi

# list newest first; remove beyond N
mapfile -t files < <(ls -1t "$dir"/ae_backup_*.tar.gz 2>/dev/null || true)

count="${#files[@]}"
if [[ "$count" -le "$keep" ]]; then
  echo "OK: $count backups <= keep=$keep (no deletions)"
  exit 0
fi

for ((i=keep; i<count; i++)); do
  rm -f "${files[$i]}"
done

echo "OK: rotated $dir (kept $keep, removed $((count-keep)))"
