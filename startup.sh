#!/bin/bash
# SentinelFlow AI — Cross-platform Startup Script for Production & Demo Scenarios
# Suitable for Railway (Linux) and Local (Windows Git Bash / Linux / macOS)

# Exit on error
set -e

echo "============================================================"
echo " Starting SentinelFlow AI Services..."
echo "============================================================"

# Detect Python virtualenv bin path
PYTHON_BIN=""
if [ -d "backend/venv/bin" ]; then
    PYTHON_BIN="backend/venv/bin"
elif [ -d "backend/venv/Scripts" ]; then
    PYTHON_BIN="backend/venv/Scripts"
fi

# Run DB Migrations
echo "==> Applying database migrations..."
if [ -n "$PYTHON_BIN" ]; then
    $PYTHON_BIN/alembic -c backend/alembic.ini upgrade head
else
    cd backend && alembic upgrade head && cd ..
fi

# Start Backend API Server
echo "==> Booting Backend API Server on Port 8000..."
if [ -n "$PYTHON_BIN" ]; then
    $PYTHON_BIN/uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 &
else
    cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 &
fi

# Start Frontend Node Server
echo "==> Launching Next.js Frontend Server on Port 3000..."
cd frontend
# Clean next build/start if built, else fallback to dev mode
if [ -d ".next" ]; then
    echo "==> Serving production build on Port 3000..."
    npm run start -- -p 3000
else
    echo "==> Production build not found. Running under development mode..."
    npm run dev -- -p 3000
fi
