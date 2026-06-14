#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../lib.sh
source "${SCRIPT_DIR}/../lib.sh"

PROJECT="/Users/oibaf/Projects/9router"
PORT=20128
PIDFILE="$(service_pid_file nine-router)"
LOGFILE="$(service_log_file nine-router)"
PROD_MARKER="${PROJECT}/.next/prerender-manifest.json"
NEXT_BIN="${PROJECT}/node_modules/.bin/next"

if [[ ! -d "${PROJECT}/node_modules" ]]; then
  echo "Installing 9router dependencies…"
  (cd "$PROJECT" && npm install)
fi

if [[ ! -x "$NEXT_BIN" ]]; then
  echo "Missing ${NEXT_BIN} — run npm install in ${PROJECT}" >&2
  exit 1
fi

if is_running "nine-router"; then
  echo "nine-router already running (pid $(cat "$PIDFILE"))"
  exit 0
fi

if port_in_use "$PORT"; then
  echo "Port ${PORT} already in use:" >&2
  lsof -iTCP:"$PORT" -sTCP:LISTEN -P >&2 || true
  exit 1
fi

if [[ -f "$PROD_MARKER" ]]; then
  echo "Starting 9router (production) on :${PORT}…"
  START_CMD=(env PORT="$PORT" "$NEXT_BIN" start -p "$PORT")
else
  echo "Starting 9router (dev) on :${PORT}…"
  START_CMD=("$NEXT_BIN" dev --webpack --port "$PORT")
fi

ensure_dirs
cd "$PROJECT"
nohup "${START_CMD[@]}" >>"$LOGFILE" 2>&1 &
echo $! >"$PIDFILE"

echo "Waiting for 9router on :${PORT}…"
for i in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
    listener_pid="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -1 || true)"
    if [[ -n "$listener_pid" ]]; then
      echo "$listener_pid" >"$PIDFILE"
    fi
    echo "Started nine-router (pid $(cat "$PIDFILE")) → http://127.0.0.1:${PORT}/dashboard"
    exit 0
  fi
  if ! kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    if port_in_use "$PORT"; then
      listener_pid="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -1 || true)"
      [[ -n "$listener_pid" ]] && echo "$listener_pid" >"$PIDFILE"
      echo "Started nine-router (pid $(cat "$PIDFILE")) → http://127.0.0.1:${PORT}/dashboard"
      exit 0
    fi
    echo "9router exited during startup; see ${LOGFILE}" >&2
    tail -25 "$LOGFILE" 2>/dev/null || true
    rm -f "$PIDFILE"
    exit 1
  fi
  sleep 1
done

echo "9router did not become healthy on :${PORT}; see ${LOGFILE}" >&2
tail -25 "$LOGFILE" 2>/dev/null || true
if [[ -f "$PIDFILE" ]]; then
  kill "$(cat "$PIDFILE")" 2>/dev/null || true
  rm -f "$PIDFILE"
fi
exit 1
