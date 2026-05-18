#!/bin/bash
set -e

echo "=== AGORA Starting ==="

# Auto-restart agent loop in background
agent_loop() {
    while true; do
        echo "[start.sh] Starting agent loop..."
        python main.py 2>&1 || true
        echo "[start.sh] Agent loop exited, restarting in 30s..."
        sleep 30
    done
}
agent_loop &

# Start dashboard backend (Railway injects $PORT)
echo "Starting dashboard on port ${PORT:-8000}..."
exec uvicorn dashboard.backend.server:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 1
