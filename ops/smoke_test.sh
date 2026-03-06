#!/usr/bin/env bash
set -euo pipefail

BASE_PUBLIC="${BASE_PUBLIC:-http://localhost:8001}"
BASE_CONSOLE="${BASE_CONSOLE:-http://localhost:8000}"

echo "[smoke] public /health"
curl -fsS "$BASE_PUBLIC/health" | python -m json.tool >/dev/null
echo "OK"

echo "[smoke] public /ready"
curl -fsS "$BASE_PUBLIC/ready" | python -m json.tool >/dev/null
echo "OK"

echo "[smoke] console /health"
curl -fsS "$BASE_CONSOLE/health" | python -m json.tool >/dev/null
echo "OK"

echo "[smoke] console /ready"
curl -fsS "$BASE_CONSOLE/ready" | python -m json.tool >/dev/null
echo "OK"

echo "[smoke] lead intake (public)"
curl -fsS -X POST "$BASE_PUBLIC/lead"   -H "Content-Type: application/json"   -d '{"name":"Smoke Test","email":"smoke@example.com","message":"hello","utm":{"utm_source":"smoke"}}'   | python -m json.tool >/dev/null
echo "OK"

echo "[smoke] done"
