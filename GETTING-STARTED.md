# SentinelFlow AI — Getting Started Guide

SentinelFlow AI is a production-inspired, cybersecurity SecOps incident response platform. It consumes container metrics, uses an anomaly detection pipeline, triggers AI agent incident correlation processes, logs tamper-evident entries into a cryptographic audit ledger, and enables human-in-the-loop remediation through a futuristic dashboard.

## Quick Start on Windows

### 1. Prerequisites
Ensure you have the following installed on your machine:
- **Python 3.11+** (Make sure to check "Add Python to PATH" during installation)
- **Node.js 18+** (with npm)

### 2. One-Click Setup
Run the bootstrap setup script to configure environment variables, initialize the Python virtual environment, install package dependencies, and verify your Node.js setup:
```powershell
# Open PowerShell in the project directory
.\setup.ps1
```

### 3. Launch Services
Run the launcher command to boot the FastAPI backend server, start the Next.js frontend dev server, and automatically launch your browser:
```bat
# From a Command Prompt or PowerShell, double-click or run:
.\run_sentinelflow.bat
```

### 4. Access URLs
- **Web Dashboard**: http://localhost:3000
- **API Swagger Documentation**: http://127.0.0.1:8000/docs

## Key Project Features
- **Dual-Factor Authentication (MFA)**: Set up and log in using standard Authenticator Apps (Google/Microsoft Authenticator) with dynamic TOTP verification.
- **Enkrypt AI Safety Guards**: Pre-assessment policy engine blocks dangerous console traversal inputs (`rm -rf`) to protect host filesystems.
- **Tamper-Evident Ledger**: Uses block hashing chain values stored in SQLite database to log automated and manual remediation steps.
- **High-Throughput Telemetry Ingestion**: Buffers cluster telemetry in memory with heuristics anomaly detectors.
- **Cluster Topology & Edge Monitor**: Visualizes kubernetes pods and nodes live with metric trends.
