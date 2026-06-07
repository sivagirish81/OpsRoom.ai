#!/usr/bin/env bash
# One-command hackathon demo: Redis → seed → backend → frontend → chaos replay
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
LOG_DIR="$ROOT/.demo-logs"
mkdir -p "$LOG_DIR"

echo "==> Starting Redis (Docker)..."
docker compose up -d redis
until docker compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; do
  sleep 1
done

if [[ ! -d .venv ]]; then
  echo "==> Creating Python virtualenv..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Installing Python dependencies..."
pip install -e ".[dev]" -q

echo "==> Seeding Kafka lag incident + runbooks..."
python -m samples.kafka_lag_incident.seed_redis

echo "==> Stopping any existing demo processes..."
for port in 8000 3000; do
  lsof -ti:"$port" | xargs kill -9 2>/dev/null || true
done

echo "==> Starting backend (port 8000)..."
nohup uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload \
  > "$LOG_DIR/backend.log" 2>&1 &
echo $! > "$LOG_DIR/backend.pid"

echo "==> Starting frontend (port 3000)..."
if [[ ! -d frontend/node_modules ]]; then
  (cd frontend && npm ci)
fi
(
  cd frontend
  nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
  echo $! > "$LOG_DIR/frontend.pid"
)

echo "==> Waiting for services..."
for _ in $(seq 1 60); do
  curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1 && break
  sleep 1
done
for _ in $(seq 1 60); do
  curl -sf http://127.0.0.1:3000 >/dev/null 2>&1 && break
  sleep 1
done

echo "==> Running chaos replay (~30s visible lag spike)..."
python -m samples.kafka_lag_incident.replay_incident --reset --chaos

WEAVE_URL="$(curl -sf http://127.0.0.1:8000/health | python3 -c "import sys,json; print(json.load(sys.stdin).get('weave') or '')" 2>/dev/null || true)"

echo ""
echo "=========================================="
echo "  OpsRoom.ai demo is ready"
echo "=========================================="
echo "  War room UI:  http://localhost:3000"
echo "  Backend API:  http://localhost:8000/health"
if [[ -n "$WEAVE_URL" ]]; then
  echo "  Weave traces: $WEAVE_URL"
fi
echo ""
echo "  Split-screen tip: UI left | Weave tab right (see README)"
echo "  Stop demo:      make demo-stop"
echo "  Re-run chaos:   make chaos"
echo "  Logs:           $LOG_DIR/"
echo "=========================================="
