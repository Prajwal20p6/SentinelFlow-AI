# ============================================================
# SentinelFlow AI — Environment Setup Bootstrap Script
# ============================================================

$ErrorActionPreference = "Stop"
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "       SENTINELFLOW AI - SYSTEM SETUP AND VERIFICATION" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# ── 1. Check Python installation ──────────────────────────────
Write-Host "[1/5] Verifying Python runtime..." -ForegroundColor Yellow
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    $pythonVersion = python --version
    Write-Host "  SUCCESS: Python detected: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "  ERROR: Python not found. Please install Python 3.11+." -ForegroundColor Red
    Exit 1
}

# ── 2. Check Node.js and NPM ──────────────────────────────────
Write-Host "[2/5] Verifying Node.js environment..." -ForegroundColor Yellow
if (Get-Command "node" -ErrorAction SilentlyContinue) {
    $nodeVersion = node --version
    $npmVersion = npm --version
    Write-Host "  SUCCESS: Node.js detected: $nodeVersion (npm: $npmVersion)" -ForegroundColor Green
} else {
    Write-Host "  ERROR: Node.js not found. Please install Node.js 18+." -ForegroundColor Red
    Exit 1
}

# ── 3. Configure environment variables ─────────────────────────
Write-Host "[3/5] Syncing environment configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "  SUCCESS: Created new .env file from .env.example" -ForegroundColor Green
} else {
    Write-Host "  SUCCESS: Existing .env file detected" -ForegroundColor Green
}

# ── 4. Setup Python Virtual Environment & Backend dependencies ──
Write-Host "[4/5] Syncing backend dependencies..." -ForegroundColor Yellow
cd backend
if (-not (Test-Path "venv")) {
    Write-Host "  Creating Python virtual environment (venv)..." -ForegroundColor Gray
    python -m venv venv
}

Write-Host "  Activating venv and installing packages..." -ForegroundColor Gray
# Install in the local active environment/venv
.\venv\Scripts\pip.exe install -r requirements.txt --quiet
Write-Host "  SUCCESS: Python packages installed." -ForegroundColor Green
cd ..

# ── 5. Setup Next.js Frontend node modules ─────────────────────
Write-Host "[5/5] Syncing frontend node packages..." -ForegroundColor Yellow
cd frontend
Write-Host "  Installing node packages (this may take a minute)..." -ForegroundColor Gray
npm install --quiet
Write-Host "  SUCCESS: Node packages successfully configured." -ForegroundColor Green
cd ..

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  SentinelFlow AI environment bootstrap completed successfully!" -ForegroundColor Green
Write-Host "  Start services by running: .\start.ps1" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
