#!/bin/bash
# F.R.I.D.A.Y. — Stop all services (uses saved PIDs, falls back to ports)
FRIDAY_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "  Shutting down FRIDAY..."

for pidfile in "$FRIDAY_ROOT/logs/backend.pid" "$FRIDAY_ROOT/logs/frontend.pid"; do
  if [ -f "$pidfile" ]; then
    PID=$(cat "$pidfile")
    NAME=$(basename "$pidfile" .pid)
    if kill -0 "$PID" 2>/dev/null; then
      kill -9 "$PID" 2>/dev/null && echo "  ✅ $NAME stopped (PID $PID)"
    fi
    rm -f "$pidfile"
  fi
done

# Fallback: anything still listening on our ports
kill -9 $(lsof -t -i:8000) 2>/dev/null && echo "  ✅ Backend stopped"
kill -9 $(lsof -t -i:5173) 2>/dev/null && echo "  ✅ Frontend stopped"

echo "  🔴 FRIDAY offline."
