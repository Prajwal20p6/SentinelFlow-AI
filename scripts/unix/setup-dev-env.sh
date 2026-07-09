#!/usr/bin/env bash
# ============================================================
# SentinelFlow AI — Unix Environment Setup (CI/CD / Linux Dev)
# ============================================================

set -e

echo "============================================================"
echo "          SENTINELFLOW AI - UNIX SETUP BOOTSTRAP"
echo "============================================================"

# ── 1. Create Virtual Environment ──
echo "[1/4] Setting up Python virtual environment..."
cd backend
python3 -m venv venv
source venv/bin/activate

# ── 2. Install Packages ──
echo "[2/4] Installing backend dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
cd ..

# ── 3. Install Frontend Packages ──
echo "[3/4] Installing frontend npm packages..."
cd frontend
npm install
cd ..

# ── 4. Verify Database Setup ──
echo "[4/4] Setting up local database schema..."
cd backend
python3 -c "from app.core.database import engine; from app.models.models import Base; Base.metadata.create_all(bind=engine)"
cd ..

echo "============================================================"
echo "Unix bootstrap setup completed successfully."
echo "============================================================"
