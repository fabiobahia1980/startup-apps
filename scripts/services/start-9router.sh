#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../lib.sh
source "${SCRIPT_DIR}/../lib.sh"

PROJECT="/Users/oibaf/Projects/9router"
PORT=20128

if [[ ! -d "${PROJECT}/node_modules" ]]; then
  echo "Installing 9router dependencies…"
  (cd "$PROJECT" && npm install)
fi

if [[ -d "${PROJECT}/.next" ]]; then
  CMD=(npm run start)
else
  CMD=(npm run dev)
fi

start_background "nine-router" "$PORT" "$PROJECT" "${CMD[@]}"
