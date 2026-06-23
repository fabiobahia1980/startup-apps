#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../lib.sh
source "${SCRIPT_DIR}/../lib.sh"

PORT=3344
start_background "opencode" "$PORT" "/Users/oibaf/Projects/opencode" \
  /opt/homebrew/bin/opencode serve --port "$PORT" --hostname "127.0.0.1"
