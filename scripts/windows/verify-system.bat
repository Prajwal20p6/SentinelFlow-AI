@echo off
title SentinelFlow AI - Verify System
echo ============================================================
echo          SentinelFlow AI - System Verification
echo ============================================================

echo [*] Checking Python...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [-] Python is not installed or not in PATH.
    goto error
)
python --version

echo [*] Checking Node.js...
node --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [-] Node.js is not installed or not in PATH.
    goto error
)
node --version

echo [*] Checking NPM...
npm --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [-] NPM is not installed or not in PATH.
    goto error
)
echo NPM Version:
npm --version

echo [*] Running system health diagnostics...
if exist "%~dp0..\..\backend\venv\Scripts\python.exe" (
    "%~dp0..\..\backend\venv\Scripts\python.exe" "%~dp0..\python\health_check.py"
) else (
    python "%~dp0..\python\health_check.py"
)

echo ============================================================
echo System check completed.
pause
exit /b 0

:error
echo [!] System verification failed. Please check pre-requisites.
pause
exit /b 1
