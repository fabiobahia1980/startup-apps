#!/usr/bin/env bash
# Install a one-shot LaunchAgent that runs the post-reboot e2e test at login.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="${HOME}/.startup-apps"
PLIST_SRC="${ROOT}/launchagents/com.startup-apps.e2e-reboot-test.plist.template"
PLIST_DST="${HOME}/Library/LaunchAgents/com.startup-apps.e2e-reboot-test.plist"
LABEL="gui/$(id -u)/com.startup-apps.e2e-reboot-test"

chmod +x "${ROOT}/scripts/e2e-reboot-test.sh"

sed \
  -e "s|__E2E_SCRIPT__|${ROOT}/scripts/e2e-reboot-test.sh|g" \
  -e "s|__STATE_DIR__|${STATE_DIR}|g" \
  "$PLIST_SRC" > "$PLIST_DST"

launchctl bootout "$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_DST"

echo "Installed one-shot e2e reboot test."
echo "  Runs at next login, waits 120s, validates all visible services + HA db_connected"
echo "  Log: ${STATE_DIR}/e2e-reboot.log"
echo ""
echo "Run now:  ${ROOT}/scripts/e2e-reboot-test.sh"
echo "Remove:   ${ROOT}/scripts/remove-e2e-reboot-test.sh"
