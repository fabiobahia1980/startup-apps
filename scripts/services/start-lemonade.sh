#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../lib.sh
source "${SCRIPT_DIR}/../lib.sh"

PORT=13305
PIDFILE="$(service_pid_file lemonade)"
LOGFILE="$(service_log_file lemonade)"
DEFAULT_BIN="/Users/oibaf/Projects/lemonade/build/lemond"
HEALTH_PATHS=("/api/v1/health" "/v1/health" "/api/v0/health")

resolve_lemond_bin() {
  if [[ -n "${LEMONADE_BIN:-}" && -x "${LEMONADE_BIN}" ]]; then
    echo "${LEMONADE_BIN}"
    return
  fi
  if [[ -x "$DEFAULT_BIN" ]]; then
    echo "$DEFAULT_BIN"
    return
  fi
  for candidate in lemond lemonade; do
    if command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return
    fi
  done
  return 1
}

LEMONADE_BIN="$(resolve_lemond_bin || true)"
if [[ -z "$LEMONADE_BIN" ]]; then
  echo "lemond not found — build Lemonade or set LEMONADE_BIN" >&2
  echo "  cd /Users/oibaf/Projects/lemonade && ./setup.sh" >&2
  exit 1
fi

if is_running "lemonade"; then
  echo "lemonade already running (pid $(cat "$PIDFILE"))"
  exit 0
fi

if port_in_use "$PORT"; then
  echo "Port ${PORT} already in use:" >&2
  lsof -iTCP:"$PORT" -sTCP:LISTEN -P >&2 || true
  exit 1
fi

ensure_dirs
cd "$(dirname "$LEMONADE_BIN")"
nohup "$LEMONADE_BIN" >>"$LOGFILE" 2>&1 &
echo $! >"$PIDFILE"

echo "Waiting for Lemonade on :${PORT}…"
for i in $(seq 1 30); do
  for path in "${HEALTH_PATHS[@]}"; do
    if curl -sf "http://127.0.0.1:${PORT}${path}" >/dev/null 2>&1; then
      listener_pid="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -1 || true)"
      if [[ -n "$listener_pid" ]]; then
        echo "$listener_pid" >"$PIDFILE"
      fi
      echo "Started lemonade (pid $(cat "$PIDFILE")) → http://127.0.0.1:${PORT}"
      exit 0
    fi
  done
  if ! kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    if port_in_use "$PORT"; then
      listener_pid="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -1 || true)"
      [[ -n "$listener_pid" ]] && echo "$listener_pid" >"$PIDFILE"
      echo "Started lemonade (pid $(cat "$PIDFILE")) → http://127.0.0.1:${PORT}"
      exit 0
    fi
    echo "lemond exited during startup; see ${LOGFILE}" >&2
    tail -20 "$LOGFILE" 2>/dev/null || true
    rm -f "$PIDFILE"
    exit 1
  fi
  sleep 1
done

echo "Lemonade did not become healthy on :${PORT}; see ${LOGFILE}" >&2
tail -20 "$LOGFILE" 2>/dev/null || true
if [[ -f "$PIDFILE" ]]; then
  kill "$(cat "$PIDFILE")" 2>/dev/null || true
  rm -f "$PIDFILE"
fi
exit 1
