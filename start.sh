#!/bin/bash
# ─────────────────────────────────────────────
#  F.R.I.D.A.Y. — One-command startup script
#  Usage: ./start.sh
# ─────────────────────────────────────────────

FRIDAY_ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$FRIDAY_ROOT/backend"
FRONTEND="$FRIDAY_ROOT/friday-ui"
BACKEND_LOG="$FRIDAY_ROOT/logs/backend.log"
FRONTEND_LOG="$FRIDAY_ROOT/logs/frontend.log"

mkdir -p "$FRIDAY_ROOT/logs"

echo ""
echo "  ███████ ██████  ██ ██████   █████  ██    ██ "
echo "  ██      ██   ██ ██ ██   ██ ██   ██  ██  ██  "
echo "  █████   ██████  ██ ██   ██ ███████   ████   "
echo "  ██      ██   ██ ██ ██   ██ ██   ██    ██    "
echo "  ██      ██   ██ ██ ██████  ██   ██    ██    "
echo ""
echo "  F.R.I.D.A.Y. — Personal AI Assistant"
echo "  Starting all services..."
echo ""

# ── Kill any stale instances ──────────────────
echo "  [1/3] Cleaning up old processes..."
for pidfile in "$FRIDAY_ROOT/logs/backend.pid" "$FRIDAY_ROOT/logs/frontend.pid"; do
  if [ -f "$pidfile" ]; then
    kill -9 "$(cat "$pidfile")" 2>/dev/null
    rm -f "$pidfile"
  fi
done
# Fallback: anything still squatting on our ports
kill -9 $(lsof -t -i:8000) 2>/dev/null
kill -9 $(lsof -t -i:5173) 2>/dev/null
sleep 1

# ── Start Backend ─────────────────────────────
echo "  [2/3] Starting backend (port 8000)..."
cd "$BACKEND"
./venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000 --no-proxy-headers > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
sleep 4

if lsof -i:8000 | grep -q LISTEN; then
    echo "  ✅ Backend running  → http://localhost:8000  (PID: $BACKEND_PID)"
else
    echo "  ❌ Backend failed to start. Check logs/backend.log"
    exit 1
fi

# ── Start Frontend ────────────────────────────
echo "  [3/3] Starting frontend (port 5173)..."
cd "$FRONTEND"
npm run dev > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
sleep 4

if lsof -i:5173 | grep -q LISTEN; then
    echo "  ✅ Frontend running → http://localhost:5173  (PID: $FRONTEND_PID)"
else
    echo "  ❌ Frontend failed to start. Check logs/frontend.log"
    exit 1
fi

# ── Save PIDs for stop script ─────────────────
echo "$BACKEND_PID" > "$FRIDAY_ROOT/logs/backend.pid"
echo "$FRONTEND_PID" > "$FRIDAY_ROOT/logs/frontend.pid"

echo ""
echo "  🟢 FRIDAY is live → http://localhost:5173"
echo "  📋 Backend logs  → $BACKEND_LOG"
echo "  📋 Frontend logs → $FRONTEND_LOG"
echo ""
echo "  Run ./stop.sh to shut everything down."
echo ""
