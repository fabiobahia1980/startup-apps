#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../lib.sh
source "${SCRIPT_DIR}/../lib.sh"

PROJECT="/Users/oibaf/Projects/ai-agent/Cursor-dashboard"
PORT=8081
BIN="${PROJECT}/target/debug/cursor-server"

if [[ ! -x "$BIN" ]]; then
  echo "Building cursor-server…"
  (cd "$PROJECT" && cargo build -p cursor-server)
fi

start_background "cursor-observability" "$PORT" "$PROJECT" "$BIN"
