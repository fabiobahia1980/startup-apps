#!/usr/bin/env bash
# Shared helpers for background service scripts.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STATE_DIR="${HOME}/.startup-apps"
PID_DIR="${STATE_DIR}/pids"
LOG_DIR="${STATE_DIR}/logs"

ensure_dirs() {
  mkdir -p "$PID_DIR" "$LOG_DIR"
}

service_pid_file() {
  echo "${PID_DIR}/$1.pid"
}

service_log_file() {
  echo "${LOG_DIR}/$1.log"
}

is_running() {
  local service_id="$1"
  local pidfile
  pidfile="$(service_pid_file "$service_id")"
  if [[ -f "$pidfile" ]]; then
    local pid
    pid="$(cat "$pidfile")"
    if kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
    rm -f "$pidfile"
  fi
  return 1
}

port_in_use() {
  local port="$1"
  lsof -iTCP:"$port" -sTCP:LISTEN -P >/dev/null 2>&1
}

start_background() {
  local service_id="$1"
  local port="$2"
  local workdir="$3"
  shift 3

  ensure_dirs
  local pidfile logfile
  pidfile="$(service_pid_file "$service_id")"
  logfile="$(service_log_file "$service_id")"

  if is_running "$service_id"; then
    echo "${service_id} already running (pid $(cat "$pidfile"))"
    exit 0
  fi

  if port_in_use "$port"; then
    echo "Port ${port} already in use for ${service_id}:" >&2
    lsof -iTCP:"$port" -sTCP:LISTEN -P >&2 || true
    exit 1
  fi

  cd "$workdir"
  nohup "$@" >>"$logfile" 2>&1 &
  echo $! >"$pidfile"
  sleep 2

  if is_running "$service_id"; then
    echo "Started ${service_id} (pid $(cat "$pidfile")) on :${port}"
  else
    echo "Failed to start ${service_id}; see ${logfile}" >&2
    tail -20 "$logfile" 2>/dev/null || true
    exit 1
  fi
}

stop_background() {
  local service_id="$1"
  local pidfile
  pidfile="$(service_pid_file "$service_id")"

  if [[ ! -f "$pidfile" ]]; then
    echo "${service_id} not running"
    exit 0
  fi

  local pid
  pid="$(cat "$pidfile")"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 10); do
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.5
    done
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
    echo "Stopped ${service_id} (pid ${pid})"
  else
    echo "${service_id} not running (stale pid)"
  fi
  rm -f "$pidfile"
}
