#!/bin/bash
# Wrapper script to run ae.cli commands with proper PYTHONPATH
# Usage: ops/scripts/ae_cli.sh <command> [args...]

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export PYTHONPATH="$ROOT/src"

python -m ae.cli "$@"
