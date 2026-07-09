# ============================================================
# SentinelFlow AI — Process Launcher & Orchestrator
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "             STARTING SENTINELFLOW AI PLATFORM" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# ── 1. Booting FastAPI Backend ───────────────────────────────
Write-Host "[1/2] Spinning up FastAPI backend server in a new window..." -ForegroundColor Yellow
cd backend
Start-Process -FilePath "venv\Scripts\python.exe" -ArgumentList "run.py" -WindowStyle Normal
Write-Host "  SUCCESS: Backend process launched." -ForegroundColor Green
cd ..

# ── 2. Booting Next.js Frontend ──────────────────────────────
Write-Host "[2/2] Spinning up Next.js dev server in a new window..." -ForegroundColor Yellow
cd frontend
Start-Process -FilePath "npm.cmd" -ArgumentList "run dev" -WindowStyle Normal
Write-Host "  SUCCESS: Next.js dev server process launched." -ForegroundColor Green
cd ..

# ── 3. Opening Browser ───────────────────────────────────────
Write-Host "Launching Web Dashboard..." -ForegroundColor Yellow
Start-Sleep -Seconds 3
Start-Process "http://localhost:3000"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  SentinelFlow AI is running!" -ForegroundColor Green
Write-Host "  - Backend API Docs: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "  - Web Dashboard:    http://localhost:3000" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
