#!/usr/bin/env bash
set -euo pipefail

LABEL="gui/$(id -u)/com.startup-apps.e2e-reboot-test"
PLIST_DST="${HOME}/Library/LaunchAgents/com.startup-apps.e2e-reboot-test.plist"

launchctl bootout "$LABEL" 2>/dev/null || true
rm -f "$PLIST_DST"
echo "Removed e2e reboot test LaunchAgent."
