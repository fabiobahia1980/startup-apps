#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../lib.sh
source "${SCRIPT_DIR}/../lib.sh"

PORT=20128
NINEROUTER_BIN="$(command -v 9router || true)"
if [[ -z "$NINEROUTER_BIN" ]]; then
  echo "9router CLI not found — run: npm i -g 9router@latest" >&2
  exit 1
fi

start_background "nine-router" "$PORT" "$HOME" \
  "$NINEROUTER_BIN" -p "$PORT" -H 127.0.0.1 -n --skip-update
