@echo off
title SentinelFlow AI - Start All Services
echo ============================================================
echo          SentinelFlow AI - Launching All Services
echo ============================================================

echo [*] Starting Backend Server in new window...
start "SentinelFlow AI Backend" "%~dp0start-backend.bat"

echo [*] Starting Frontend Server in new window...
start "SentinelFlow AI Frontend" "%~dp0start-frontend.bat"

echo [*] Launching Web Dashboard in browser...
timeout /t 3 /nobreak >nul
start "" "http://localhost:3000"

echo ============================================================
echo Both services have been launched in separate windows.
echo - Web Dashboard:    http://localhost:3000
echo - Swagger Docs:     http://127.0.0.1:8000/docs
echo ============================================================
