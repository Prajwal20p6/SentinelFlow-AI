@echo off
title SentinelFlow AI - Stop All Services
echo ============================================================
echo          SentinelFlow AI - Stopping All Services
echo ============================================================

echo [*] Terminating Python/Uvicorn processes...
taskkill /F /IM python.exe >nul 2>&1
if %ERRORLEVEL% eq 0 (
    echo [+] Python backend terminated.
) else (
    echo [*] No Python process was running.
)

echo [*] Terminating Node/Next.js processes...
taskkill /F /IM node.exe >nul 2>&1
if %ERRORLEVEL% eq 0 (
    echo [+] Node/Next.js frontend terminated.
) else (
    echo [*] No Node process was running.
)

echo ============================================================
echo All services stopped.
pause
