#!/usr/bin/env bash
# Single-command startup for the Support Ticket AI System
# Starts FastAPI (port 8000) and Streamlit UI (port 8501) in the background.
# Tested on Linux/macOS/Git Bash for Windows.

set -euo pipefail

echo "🚀 Starting Support Ticket AI System..."

PY=$(command -v python3 || command -v python)

# Start FastAPI
"$PY" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!
echo "   FastAPI PID: $UVICORN_PID (http://localhost:8000)"

# Start Streamlit
"$PY" -m streamlit run ui/streamlit_app.py --server.port 8501 --server.headless true &
STREAMLIT_PID=$!
echo "   Streamlit PID: $STREAMLIT_PID (http://localhost:8501)"

# Trap exit signals to kill children
cleanup() {
  echo ""
  echo "🛑 Shutting down..."
  kill "$UVICORN_PID" "$STREAMLIT_PID" 2>/dev/null || true
  wait "$UVICORN_PID" "$STREAMLIT_PID" 2>/dev/null || true
  echo "✅ Done."
}
trap cleanup EXIT INT TERM

# Wait forever (until Ctrl-C)
wait