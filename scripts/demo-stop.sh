#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/.demo-logs"

for port in 8000 3000; do
  lsof -ti:"$port" | xargs kill -9 2>/dev/null || true
done

if [[ -d "$LOG_DIR" ]]; then
  for name in backend frontend; do
    pid_file="$LOG_DIR/${name}.pid"
    if [[ -f "$pid_file" ]]; then
      kill -9 "$(cat "$pid_file")" 2>/dev/null || true
      rm -f "$pid_file"
    fi
  done
fi

echo "Demo processes stopped (ports 8000 and 3000). Redis left running — use 'docker compose down' to stop it."
