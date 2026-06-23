#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../lib.sh
source "${SCRIPT_DIR}/../lib.sh"

PORT=20128
PIDFILE="$(service_pid_file nine-router)"

stop_pid() {
  local pid="$1"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 10); do
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.5
    done
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
    echo "Stopped nine-router (pid ${pid})"
  fi
}

if [[ -f "$PIDFILE" ]]; then
  stop_pid "$(cat "$PIDFILE")"
  rm -f "$PIDFILE"
fi

pkill -f '/opt/homebrew/bin/9router' 2>/dev/null || true
pkill -f '9router.*-p[ =]'"$PORT" 2>/dev/null || true

if port_in_use "$PORT"; then
  listener_pid="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -1 || true)"
  if [[ -n "$listener_pid" ]]; then
    stop_pid "$listener_pid"
  fi
fi

echo "nine-router stopped"
