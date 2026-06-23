#!/usr/bin/env bash
# Detect known autostart conflicts and misconfigurations.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ISSUES=0
PORT_ISSUES=0

warn() {
  printf 'WARN: %s\n' "$*"
  ISSUES=$((ISSUES + 1))
}

ok() {
  printf 'OK:   %s\n' "$*"
}

has_login_item() {
  local name="$1"
  osascript -e 'tell application "System Events" to get the name of every login item' 2>/dev/null \
    | tr ',' '\n' \
    | sed 's/^[[:space:]]*//' \
    | grep -Fxq "$name"
}

brew_service_running() {
  local service="$1"
  brew services info "$service" 2>/dev/null | grep -q 'Running: true'
}

port_listener() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN 2>/dev/null | awk 'NR==2 {print $1, $2, $9}'
}

echo "==> Startup Apps doctor"

if has_login_item "oMLX"; then
  if brew_service_running "jundot/omlx/omlx" || [[ -n "$(port_listener 8000)" ]]; then
    warn "oMLX Login Item auto-launches /Applications/oMLX.app while brew service already serves :8000"
    echo "      Fix: ./scripts/fix-omlx-login-item.sh"
    echo "      Or: System Settings → General → Login Items → remove oMLX"
  else
    ok "oMLX Login Item present (brew service not running yet)"
  fi
else
  ok "oMLX Login Item not configured"
fi

if launchctl print "gui/$(id -u)/com.startup-apps.manager" >/dev/null 2>&1; then
  ok "Startup Apps LaunchAgent loaded"
else
  warn "Startup Apps LaunchAgent not loaded (run ./scripts/install.sh)"
fi

if curl -fsS --max-time 3 http://127.0.0.1:9090/api/status >/dev/null 2>&1; then
  ok "Dashboard responding on :9090"
else
  warn "Dashboard not responding on :9090"
fi

echo ""
echo "==> Port registry"
if [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PORT_ISSUES=0
  (
    cd "${ROOT}"
    "${ROOT}/.venv/bin/python" -m startup_manager doctor
  ) || PORT_ISSUES=$?
  ISSUES=$((ISSUES + PORT_ISSUES))
else
  warn "Python venv not found (run ./scripts/install.sh)"
fi

echo ""
if (( ISSUES > 0 )); then
  echo "Found ${ISSUES} issue(s)."
  exit 1
fi

echo "No issues found."
exit 0
