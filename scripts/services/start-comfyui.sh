#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../lib.sh
source "${SCRIPT_DIR}/../lib.sh"

PORT=8188
PROJECT="/Users/oibaf/Projects/comfyui"
PYTHON="${PROJECT}/venv/bin/python"

if brew services info jundot/omlx/omlx 2>/dev/null | grep -q 'Running: true'; then
  echo "Stopping OMLX (mutually exclusive with ComfyUI)…" >&2
  brew services stop jundot/omlx/omlx
fi

if [[ ! -x "$PYTHON" ]]; then
  echo "Missing ${PYTHON} — create the ComfyUI venv first" >&2
  exit 1
fi

start_background "comfyui" "$PORT" "$PROJECT" \
  "$PYTHON" main.py --disable-auto-launch --port "$PORT"
