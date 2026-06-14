#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if docker info >/dev/null 2>&1; then
  version="$(docker info --format '{{.ServerVersion}}' 2>/dev/null || echo unknown)"
  echo "Docker Desktop already running (v${version})"
  exit 0
fi

echo "Starting Docker Desktop…"
for app in Docker "Docker Desktop"; do
  if open -a "$app" 2>/dev/null; then
    break
  fi
done

echo "Waiting for Docker daemon…"
for i in $(seq 1 60); do
  if docker info >/dev/null 2>&1; then
    version="$(docker info --format '{{.ServerVersion}}' 2>/dev/null || echo unknown)"
    echo "Docker Desktop ready after ${i}s (v${version})"
    exit 0
  fi
  sleep 1
done

echo "Docker Desktop did not become ready within 60s" >&2
exit 1
