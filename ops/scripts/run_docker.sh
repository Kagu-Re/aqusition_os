#!/usr/bin/env bash
set -euo pipefail

# One-command Docker run.
#
# Usage:
#   ./ops/scripts/run_docker.sh public
#   ./ops/scripts/run_docker.sh console
#   ./ops/scripts/run_docker.sh all
#
# Requirements: docker + docker compose plugin.

mode="${1:-all}"

if [[ ! -f ".env" ]]; then
  if [[ -f ".env.example" ]]; then
    cp .env.example .env
    echo "Created .env from .env.example (edit secrets as needed)."
  else
    echo "Missing .env and .env.example" >&2
    exit 2
  fi
fi

case "$mode" in
  public)
    docker compose --profile public up --build -d
    echo "Public API: http://localhost:8000"
    ;;
  console)
    docker compose --profile console up --build -d
    echo "Console: http://localhost:8001"
    ;;
  all)
    docker compose --profile public --profile console up --build -d
    echo "Public API: http://localhost:8000"
    echo "Console:   http://localhost:8001"
    ;;
  *)
    echo "Unknown mode: $mode (public|console|all)" >&2
    exit 2
    ;;
esac
