#!/usr/bin/env bash
# Post-reboot end-to-end validation for the startup-apps manager.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="${HOME}/.startup-apps"
LOG_FILE="${STATE_DIR}/e2e-reboot.log"
DASHBOARD_URL="http://127.0.0.1:9090"
HA_HEALTH_URL="http://127.0.0.1:8080/api/health"
LAUNCH_AGENT="gui/$(id -u)/com.startup-apps.manager"
E2E_AGENT="gui/$(id -u)/com.startup-apps.e2e-reboot-test"

WAIT_SECONDS="${WAIT_SECONDS:-120}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-30}"
RETRY_SECONDS="${RETRY_SECONDS:-10}"

log() {
  printf '%s %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$*" | tee -a "$LOG_FILE"
}

fail() {
  log "FAIL: $*"
  exit 1
}

pass() {
  log "PASS: $*"
}

check_launch_agent() {
  if launchctl print "$LAUNCH_AGENT" >/dev/null 2>&1; then
    local state
    state="$(launchctl print "$LAUNCH_AGENT" 2>/dev/null | awk -F'= ' '/^[[:space:]]*state =/{print $2; exit}')"
    pass "LaunchAgent running (state=${state:-unknown})"
    return 0
  fi
  return 1
}

check_manager_process() {
  if pgrep -f "startup_manager menubar" >/dev/null 2>&1; then
    pass "Menu bar manager process running"
    return 0
  fi
  return 1
}

check_dashboard_summary() {
  local payload up total
  payload="$(curl -fsS --max-time 5 "${DASHBOARD_URL}/api/status")"
  read -r up total <<<"$(python3 - <<'PY' "$payload"
import json, sys
data = json.loads(sys.argv[1])
summary = data["summary"]
print(summary["up"], summary["total"])
PY
)"
  if [[ "$up" == "$total" && "$total" == "7" ]]; then
    pass "Dashboard health ${up}/${total}"
    printf '%s\n' "$payload" >>"$LOG_FILE"
    return 0
  fi
  log "Dashboard health ${up}/${total} (expected 7/7)"
  return 1
}

check_ha_db() {
  local payload connected
  payload="$(curl -fsS --max-time 5 "$HA_HEALTH_URL")"
  connected="$(python3 - <<'PY' "$payload"
import json, sys
data = json.loads(sys.argv[1])
print("true" if data.get("db_connected") else "false")
PY
)"
  if [[ "$connected" == "true" ]]; then
    pass "HA agent db_connected=true"
    return 0
  fi
  log "HA agent db_connected=false"
  return 1
}

check_autostart_conflicts() {
  if osascript -e 'tell application "System Events" to get the name of every login item' 2>/dev/null \
    | tr ',' '\n' \
    | sed 's/^[[:space:]]*//' \
    | grep -Fxq "oMLX"; then
    if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
      log "WARN: oMLX Login Item may conflict with brew service on :8000 — run ./scripts/fix-omlx-login-item.sh"
    fi
  fi
}

run_checks() {
  check_launch_agent && check_manager_process && check_dashboard_summary && check_ha_db
}

cleanup_e2e_agent() {
  launchctl bootout "$E2E_AGENT" >/dev/null 2>&1 || true
}

main() {
  mkdir -p "$STATE_DIR"
  : >"$LOG_FILE"
  log "Starting post-reboot e2e test"

  if [[ "${1:-}" == "--post-login" ]]; then
    log "Waiting ${WAIT_SECONDS}s for login autostart to settle"
    sleep "$WAIT_SECONDS"
  fi

  check_autostart_conflicts || true

  local attempt=1
  while (( attempt <= MAX_ATTEMPTS )); do
    log "Attempt ${attempt}/${MAX_ATTEMPTS}"
    if run_checks; then
      log "E2E reboot test succeeded"
      cleanup_e2e_agent
      exit 0
    fi
    sleep "$RETRY_SECONDS"
    ((attempt += 1))
  done

  fail "Services did not reach 7/7 within $((WAIT_SECONDS + MAX_ATTEMPTS * RETRY_SECONDS))s"
}

main "$@"
