#!/usr/bin/env bash
# Authentix — one-step setup & launch (macOS / Linux)
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

PY=./.venv/bin/python
echo "Installing Python dependencies..."
"$PY" -m pip install --upgrade pip -q
"$PY" -m pip install -r requirements.txt -q

# Build the React UI when Node is available (server.py falls back to web/ otherwise)
if command -v npm >/dev/null 2>&1 && [ ! -d frontend/dist ]; then
  echo "Building the React frontend..."
  npm --prefix frontend install --no-audit --no-fund
  npm --prefix frontend run build
fi

if [ "$#" -gt 0 ]; then
  exec "$PY" -m authentix "$@"
else
  echo
  echo "Authentix running at http://127.0.0.1:8000  (Ctrl+C to stop)"
  echo
  exec "$PY" server.py
fi
