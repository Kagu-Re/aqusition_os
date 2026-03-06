#!/usr/bin/env bash
set -euo pipefail

# Stop stack (keeps volume by default).
# Usage:
#   ./ops/scripts/stop_docker.sh
#   ./ops/scripts/stop_docker.sh --purge

purge="${1:-}"

docker compose down

if [[ "$purge" == "--purge" ]]; then
  docker volume rm ae_data || true
  echo "Purged ae_data volume."
fi
