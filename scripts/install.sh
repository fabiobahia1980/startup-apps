#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="${HOME}/.startup-apps"
VENV="${ROOT}/.venv"
PYTHON="${VENV}/bin/python"
PLIST_SRC="${ROOT}/launchagents/com.startup-apps.manager.plist.template"
PLIST_DST="${HOME}/Library/LaunchAgents/com.startup-apps.manager.plist"

echo "==> Startup Apps installer"
mkdir -p "$STATE_DIR/pids" "$STATE_DIR/logs"

if [[ ! -d "$VENV" ]]; then
  echo "==> Creating virtualenv"
  python3 -m venv "$VENV"
fi

echo "==> Installing Python dependencies"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r "${ROOT}/requirements.txt"

echo "==> Making scripts executable"
chmod +x "${ROOT}/scripts/lib.sh"
chmod +x "${ROOT}/scripts/services/"*.sh
chmod +x "${ROOT}/scripts/doctor.sh"
chmod +x "${ROOT}/scripts/validate.py"
chmod +x "${ROOT}/scripts/fix-omlx-login-item.sh"
chmod +x "${ROOT}/scripts/e2e-reboot-test.sh"
chmod +x "${ROOT}/scripts/install-e2e-reboot-test.sh"
chmod +x "${ROOT}/scripts/remove-e2e-reboot-test.sh"

echo "==> Installing LaunchAgent"
sed \
  -e "s|__VENV_PYTHON__|${PYTHON}|g" \
  -e "s|__PROJECT_ROOT__|${ROOT}|g" \
  -e "s|__STATE_DIR__|${STATE_DIR}|g" \
  "$PLIST_SRC" > "$PLIST_DST"

launchctl bootout "gui/$(id -u)/com.startup-apps.manager" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_DST"
launchctl enable "gui/$(id -u)/com.startup-apps.manager"
launchctl kickstart -k "gui/$(id -u)/com.startup-apps.manager"

echo ""
echo "Installed."
echo "  Dashboard: http://127.0.0.1:9090"
echo "  Menu bar:  look for ● / ◐ / ○ icon titled Apps"
echo "  Config:    ${ROOT}/config/services.yaml"
echo "  Logs:      ${STATE_DIR}/logs/"
echo ""
echo "Manual run:  cd ${ROOT} && ${PYTHON} -m startup_manager menubar"
