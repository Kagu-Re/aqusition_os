#!/usr/bin/env bash
set -euo pipefail

# Backup utility for Acquisition Engine.
#
# Modes:
# 1) Docker (recommended): back up named volume `ae_data` by spinning up a throwaway alpine container.
# 2) Local path: tar a directory directly.
#
# Usage:
#   ./ops/scripts/backup.sh docker ./backups
#   ./ops/scripts/backup.sh path  ./data ./backups
#
# Output:
#   backups/ae_backup_YYYYmmdd_HHMMSS.tar.gz

mode="${1:-docker}"
src="${2:-}"
dest="${3:-}"

timestamp="$(date -u +%Y%m%d_%H%M%S)"

if [[ "$mode" == "docker" ]]; then
  outdir="${2:-./backups}"
  mkdir -p "$outdir"
  outfile="$outdir/ae_backup_${timestamp}.tar.gz"

  # expects docker compose volume name 'ae_data' (see docker-compose.yml)
  docker run --rm     -v ae_data:/data:ro     -v "$(pwd)/$outdir":/out     alpine:3.20     sh -c "tar -czf /out/$(basename "$outfile") -C /data ."

  echo "OK: $outfile"
  exit 0
fi

if [[ "$mode" == "path" ]]; then
  if [[ -z "${src}" || -z "${dest}" ]]; then
    echo "Usage: ./ops/scripts/backup.sh path <src_dir> <dest_dir>" >&2
    exit 2
  fi
  mkdir -p "$dest"
  outfile="$dest/ae_backup_${timestamp}.tar.gz"
  tar -czf "$outfile" -C "$src" .
  echo "OK: $outfile"
  exit 0
fi

echo "Unknown mode: $mode (use: docker | path)" >&2
exit 2
