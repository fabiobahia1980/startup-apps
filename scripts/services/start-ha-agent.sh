#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../lib.sh
source "${SCRIPT_DIR}/../lib.sh"

PROJECT="/Users/oibaf/Projects/ha-local-agent-mm"
PORT=8080

if [[ ! -f "${PROJECT}/.env" ]]; then
  echo "Missing ${PROJECT}/.env — copy .env.rust.example and configure tokens" >&2
  exit 1
fi

if [[ ! -f "${PROJECT}/frontend/dist/index.html" ]]; then
  echo "Building HA agent UI (first run)…"
  "${PROJECT}/scripts/build-ui.sh"
fi

if command -v docker >/dev/null 2>&1; then
  if ! docker compose -f "${PROJECT}/docker-compose.yml" ps --status running 2>/dev/null | grep -q postgres; then
    docker compose -f "${PROJECT}/docker-compose.yml" up -d postgres
  fi
fi

BIN="${PROJECT}/backend/target/release/ha-agent-backend"
if [[ ! -x "$BIN" ]]; then
  echo "Building ha-agent-backend (release)…"
  (cd "${PROJECT}/backend" && cargo build --release)
fi

start_background "ha-agent" "$PORT" "${PROJECT}/backend" \
  env NO_COLOR=false "$BIN"
