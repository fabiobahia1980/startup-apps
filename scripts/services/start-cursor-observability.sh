#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../lib.sh
source "${SCRIPT_DIR}/../lib.sh"

PROJECT="/Users/oibaf/Projects/ai-agent/Cursor-dashboard"
PORT=8081
MANAGER_PID="$(service_pid_file cursor-observability)"
PROJECT_PID="/tmp/cursor-server-${PORT}.pid"

if [[ ! -f "${PROJECT}/.env" ]]; then
  echo "Missing ${PROJECT}/.env — copy .env.example" >&2
  exit 1
fi

"${SCRIPT_DIR}/start-orbstack.sh"

"${PROJECT}/scripts/start-server.sh"

if [[ -f "$PROJECT_PID" ]]; then
  ensure_dirs
  cp "$PROJECT_PID" "$MANAGER_PID"
fi
