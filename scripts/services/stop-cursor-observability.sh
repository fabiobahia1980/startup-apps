#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../lib.sh
source "${SCRIPT_DIR}/../lib.sh"

PORT=8081
PROJECT_PID="/tmp/cursor-server-${PORT}.pid"
MANAGER_PID="$(service_pid_file cursor-observability)"

if [[ -f "$PROJECT_PID" ]]; then
  pid="$(cat "$PROJECT_PID")"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    echo "Stopped cursor-observability (pid ${pid})"
  fi
  rm -f "$PROJECT_PID"
fi

rm -f "$MANAGER_PID"
echo "cursor-observability stopped"
