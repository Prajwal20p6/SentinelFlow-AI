# ============================================================
# SentinelFlow AI — Process Launcher & Orchestrator
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "             STARTING SENTINELFLOW AI PLATFORM" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# ── 1. Booting FastAPI Backend ───────────────────────────────
Write-Host "[1/2] Spinning up FastAPI backend server..." -ForegroundColor Yellow
cd backend
# Run backend via venv
Start-Process -FilePath "venv\Scripts\python.exe" -ArgumentList "run.py" -NoNewWindow
Write-Host "  SUCCESS: Backend started in background process." -ForegroundColor Green
cd ..

# ── 2. Booting Next.js Frontend ──────────────────────────────
Write-Host "[2/2] Spinning up Next.js dev server..." -ForegroundColor Yellow
cd frontend
Start-Process -FilePath "npm.cmd" -ArgumentList "run dev" -NoNewWindow
Write-Host "  SUCCESS: Next.js dev server started in background." -ForegroundColor Green
cd ..

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  SentinelFlow AI is spinning up! Service availability:" -ForegroundColor Green
Write-Host "  - FastAPI Core Swagger docs: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "  - Next.js Web Dashboard:     http://localhost:3000" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
