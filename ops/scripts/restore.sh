#!/usr/bin/env bash
set -euo pipefail

# Restore utility for Acquisition Engine.
#
# Usage:
#   ./ops/scripts/restore.sh docker ./backups/ae_backup_....tar.gz
#   ./ops/scripts/restore.sh path  ./backups/ae_backup_....tar.gz ./data
#
# WARNING:
# - Docker mode wipes the target volume before restoring.

mode="${1:-docker}"
archive="${2:-}"
target="${3:-}"

if [[ -z "$archive" ]]; then
  echo "Archive required." >&2
  exit 2
fi
if [[ ! -f "$archive" ]]; then
  echo "Archive not found: $archive" >&2
  exit 2
fi

if [[ "$mode" == "docker" ]]; then
  # wipe + restore into ae_data
  docker run --rm -v ae_data:/data alpine:3.20 sh -c "rm -rf /data/*"
  docker run --rm     -v ae_data:/data     -v "$(pwd)":/work     alpine:3.20     sh -c "tar -xzf /work/${archive} -C /data"
  echo "OK: restored into docker volume ae_data"
  exit 0
fi

if [[ "$mode" == "path" ]]; then
  if [[ -z "$target" ]]; then
    echo "Usage: ./ops/scripts/restore.sh path <archive.tar.gz> <target_dir>" >&2
    exit 2
  fi
  mkdir -p "$target"
  rm -rf "$target"/*
  tar -xzf "$archive" -C "$target"
  echo "OK: restored into $target"
  exit 0
fi

echo "Unknown mode: $mode (use: docker | path)" >&2
exit 2
