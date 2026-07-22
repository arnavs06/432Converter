#!/usr/bin/env bash
#
# 432 Converter launcher.
# Installs Python + npm deps, starts FastAPI (:8000) and Vite (:5173),
# then opens the browser. Ctrl-C stops both servers.

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

# --- ffmpeg check -----------------------------------------------------------
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "WARNING: ffmpeg not found on PATH. Install it first:"
  echo "  macOS:   brew install ffmpeg"
  echo "  Windows: choco install ffmpeg   (or download from ffmpeg.org)"
fi

# --- Python backend ---------------------------------------------------------
echo "==> Setting up Python backend"
cd "$BACKEND"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# Call the venv binaries directly so a shell `python` alias can't shadow them.
VENV_PY="$BACKEND/.venv/bin/python"
"$VENV_PY" -m pip install --quiet --upgrade pip
"$VENV_PY" -m pip install --quiet -r requirements.txt

echo "==> Starting FastAPI on http://localhost:8000"
"$VENV_PY" -m uvicorn main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# --- Frontend ---------------------------------------------------------------
echo "==> Setting up frontend"
cd "$FRONTEND"
if [ ! -d "node_modules" ]; then
  npm install
fi

echo "==> Starting Vite on http://localhost:5173"
npm run dev &
FRONTEND_PID=$!

# --- Open browser -----------------------------------------------------------
sleep 3
URL="http://localhost:5173"
if command -v open >/dev/null 2>&1; then
  open "$URL"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL"
fi

cleanup() {
  echo ""
  echo "==> Shutting down"
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  exit 0
}
trap cleanup INT TERM

echo ""
echo "432 Converter is running. Press Ctrl-C to stop."
wait
