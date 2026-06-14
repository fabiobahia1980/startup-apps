#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../lib.sh
source "${SCRIPT_DIR}/../lib.sh"

PROJECT="/Users/oibaf/Projects/ha-local-agent-mm"
PORT=8080
POSTGRES_PORT=5434
COMPOSE="${PROJECT}/docker-compose.yml"
PIDFILE="$(service_pid_file ha-agent)"
LOGFILE="$(service_log_file ha-agent)"
BIN="${PROJECT}/target/release/ha-agent-backend"
DATABASE_URL="postgres://ha_agent:ha_agent@127.0.0.1:${POSTGRES_PORT}/ha_agent"

if [[ ! -f "${PROJECT}/.env" ]]; then
  echo "Missing ${PROJECT}/.env — copy .env.rust.example and configure tokens" >&2
  exit 1
fi

if [[ ! -f "${PROJECT}/frontend/dist/index.html" ]]; then
  echo "Building HA agent UI (first run)…"
  "${PROJECT}/scripts/build-ui.sh"
fi

if command -v docker >/dev/null 2>&1; then
  if ! docker info >/dev/null 2>&1; then
    echo "Docker is not running — required for HA Postgres on :${POSTGRES_PORT}" >&2
    exit 1
  fi
  echo "Starting HA Postgres on host :${POSTGRES_PORT}…"
  docker compose -f "$COMPOSE" up -d postgres
  echo "Waiting for HA Postgres…"
  for i in $(seq 1 30); do
    if docker compose -f "$COMPOSE" exec -T postgres pg_isready -U ha_agent -d ha_agent >/dev/null 2>&1; then
      break
    fi
    if [[ "$i" -eq 30 ]]; then
      echo "HA Postgres did not become ready on :${POSTGRES_PORT}" >&2
      exit 1
    fi
    sleep 1
  done
  if docker compose -f "$COMPOSE" ps --status running 2>/dev/null | grep -q backend; then
    echo "Stopping Docker backend (native server serves the UI on :8080)…"
    docker compose -f "$COMPOSE" stop backend
  fi
fi

if is_running "ha-agent"; then
  echo "ha-agent already running (pid $(cat "$PIDFILE"))"
  exit 0
fi

if port_in_use "$PORT"; then
  echo "Port ${PORT} in use — stopping conflicting process…" >&2
  listener_pid="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -1 || true)"
  if [[ -n "$listener_pid" ]]; then
    kill "$listener_pid" 2>/dev/null || true
    sleep 2
  fi
fi

if [[ ! -x "$BIN" ]]; then
  echo "Building ha-agent-backend (release)…"
  (cd "${PROJECT}" && cargo build --release -p ha-agent-backend)
fi

ensure_dirs
cd "${PROJECT}/backend"
nohup env NO_COLOR=false DATABASE_URL="$DATABASE_URL" "$BIN" >>"$LOGFILE" 2>&1 &
echo $! >"$PIDFILE"

echo "Waiting for HA agent on :${PORT}…"
for i in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
    health="$(curl -sf "http://127.0.0.1:${PORT}/api/health" || true)"
    if echo "$health" | grep -q '"db_connected":true'; then
      if curl -sf "http://127.0.0.1:${PORT}/" -o /dev/null -w "%{http_code}" | grep -qE '^(200|304)$'; then
        listener_pid="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -1 || true)"
        [[ -n "$listener_pid" ]] && echo "$listener_pid" >"$PIDFILE"
        echo "Started ha-agent (pid $(cat "$PIDFILE")) → http://127.0.0.1:${PORT}"
        exit 0
      fi
    fi
  fi
  if ! kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "ha-agent-backend exited during startup; see ${LOGFILE}" >&2
    tail -25 "$LOGFILE" 2>/dev/null || true
    rm -f "$PIDFILE"
    exit 1
  fi
  sleep 1
done

echo "HA agent did not become healthy on :${PORT}; see ${LOGFILE}" >&2
tail -25 "$LOGFILE" 2>/dev/null || true
kill "$(cat "$PIDFILE")" 2>/dev/null || true
rm -f "$PIDFILE"
exit 1
