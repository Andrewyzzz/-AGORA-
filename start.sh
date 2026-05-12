#!/bin/bash
set -e

echo "=== AGORA Starting ==="

# Start agent loop in background
echo "Starting agent loop..."
python main.py &
AGENT_PID=$!

# Start dashboard backend (Railway injects $PORT)
echo "Starting dashboard on port ${PORT:-8000}..."
uvicorn dashboard.backend.server:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 1

# If uvicorn exits, kill agents too
kill $AGENT_PID 2>/dev/null
