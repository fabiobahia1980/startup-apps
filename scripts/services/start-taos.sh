#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../lib.sh
source "${SCRIPT_DIR}/../lib.sh"

PROJECT="/Users/oibaf/Projects/taos"
PYTHON="${PROJECT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3)"
fi

start_background "taos" 6969 "$PROJECT" \
  "$PYTHON" -m tinyagentos
