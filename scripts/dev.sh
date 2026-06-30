#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== Aevix Development Environment ==="
echo ""

# ── Backend ─────────────────────────────────────────────────────
start_backend() {
  echo "→ Starting backend..."
  cd "$ROOT_DIR/backend"

  if [ ! -d ".venv" ]; then
    echo "  Creating virtual environment..."
    python -m venv .venv
  fi

  source .venv/Scripts/activate
  pip install -q -e ".[dev]"

  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
  BACKEND_PID=$!
  cd "$ROOT_DIR"
  echo "  Backend started (PID: $BACKEND_PID)"
}

# ── Frontend ────────────────────────────────────────────────────
start_frontend() {
  echo "→ Starting frontend..."
  cd "$ROOT_DIR/frontend"

  if [ ! -d "node_modules" ]; then
    npm install
  fi

  npm run dev &
  FRONTEND_PID=$!
  cd "$ROOT_DIR"
  echo "  Frontend started (PID: $FRONTEND_PID)"
}

# ── Cleanup ─────────────────────────────────────────────────────
cleanup() {
  echo ""
  echo "→ Shutting down..."
  [ -n "${BACKEND_PID:-}" ] && kill "$BACKEND_PID" 2>/dev/null
  [ -n "${FRONTEND_PID:-}" ] && kill "$FRONTEND_PID" 2>/dev/null
  exit 0
}

trap cleanup SIGINT SIGTERM

# ── Main ────────────────────────────────────────────────────────
start_backend
start_frontend

echo ""
echo "  Backend:  http://localhost:8000"
echo "  Docs:     http://localhost:8000/docs"
echo "  Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services."
echo ""

wait
