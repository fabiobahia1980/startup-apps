#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../lib.sh
source "${SCRIPT_DIR}/../lib.sh"

PORT=13305
LEMONADE_BIN=""
for candidate in lemond lemonade; do
  if command -v "$candidate" >/dev/null 2>&1; then
    LEMONADE_BIN="$(command -v "$candidate")"
    break
  fi
done

if [[ -z "$LEMONADE_BIN" ]]; then
  echo "lemonade/lemond not found in PATH — install Lemonade or set autostart: false" >&2
  exit 1
fi

start_background "lemonade" "$PORT" "$(dirname "$LEMONADE_BIN")" "$LEMONADE_BIN"
