#!/usr/bin/env bash
# Remove oMLX GUI login item so brew-managed `omlx serve` owns port 8000.
set -euo pipefail

if ! osascript -e 'tell application "System Events" to get the name of every login item' 2>/dev/null \
  | tr ',' '\n' \
  | sed 's/^[[:space:]]*//' \
  | grep -Fxq "oMLX"; then
  echo "oMLX is not a login item — nothing to do."
  exit 0
fi

echo "Removing oMLX from Login Items..."
osascript -e 'tell application "System Events" to delete login item "oMLX"'
echo "Done. oMLX server continues via brew service on http://127.0.0.1:8000/admin"
echo "Re-open /Applications/oMLX.app manually only when you need the GUI."
