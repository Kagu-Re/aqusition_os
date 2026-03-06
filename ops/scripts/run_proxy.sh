#!/usr/bin/env bash
set -euo pipefail

# Run with reverse proxy (Caddy) on localhost:8080
# - Public API: http://localhost:8080/api/
# - Console:    http://localhost:8080/console  (basic auth)
#
# Requirements:
# - docker + docker compose plugin
# - set AE_CONSOLE_PASS_HASH in .env (see .env.example)

if [[ ! -f ".env" ]]; then
  cp .env.example .env
  echo "Created .env from .env.example (edit secrets as needed)."
fi

# Warn if console hash is missing
if ! grep -q "^AE_CONSOLE_PASS_HASH=" .env || grep -q "^AE_CONSOLE_PASS_HASH=$" .env; then
  echo "WARNING: AE_CONSOLE_PASS_HASH is empty. Console auth will not work." >&2
  echo "Generate it: docker run --rm caddy:2 caddy hash-password --plaintext 'yourpass'" >&2
fi

docker compose --profile public --profile console --profile proxy up --build -d
echo "Proxy:      http://localhost:8080"
echo "Public API: http://localhost:8080/api/"
echo "Console:    http://localhost:8080/console"
