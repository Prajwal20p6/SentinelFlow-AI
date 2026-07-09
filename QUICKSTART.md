# SentinelFlow AI — 5-Minute Quick Start Guide

This guide gets your local development environment for SentinelFlow AI up and running.

---

## 1. Prerequisites

Ensure you have the following installed on your machine:
- **Node.js**: Version 20.0+ (with npm)
- **Python**: Version 3.11+
- **Git**

---

## 2. Fast Setup (PowerShell / Windows)

SentinelFlow AI provides setup automation scripts to configure virtual environments, databases, and start services.

1. **Clone the repository**:
   ```powershell
   git clone https://github.com/hidevs-hackathon/sentinelflow-ai.git
   cd sentinelflow-ai
   ```
2. **Execute the Setup Script**:
   Installs python modules, initializes the SQLite database schema, and seeds default CRISPE prompt templates:
   ```powershell
   # Runs virtual env configuration
   .\setup.ps1
   ```
3. **Start All Services**:
   Launches the FastAPI backend server, runs Next.js development server, and opens your default browser at `http://localhost:3000`:
   ```powershell
   .\start.ps1
   ```

---

## 3. Manual Startup Checks

If you prefer starting services in dedicated windows:

### Startup Backend
```bash
cd backend
python -m venv venv
# Activate virtual env
source venv/bin/activate  # Unix
venv\Scripts\activate     # Windows

# Install and start
pip install -r requirements.txt
python ../scripts/python/setup_databases.py
uvicorn app.main:app --reload --port 8000
```
API is accessible at `http://localhost:8000/docs`.

### Startup Frontend
```bash
cd frontend
npm install
npm run dev
```
Dashboard is accessible at `http://localhost:3000`.

---

## 4. Run Verification Suite

Verify systems coordination using the automated E2E integration verification script:
```powershell
# Windows:
.\venv\Scripts\python scripts/python/verify_sentinelflow.py
```
This performs user login, inserts telemetry anomalies, verifies state transitions, checks cryptographic chains, and pulls OpenTelemetry metrics data.
