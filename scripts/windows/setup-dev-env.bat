@echo off
title SentinelFlow AI - Setup Dev Environment
echo ============================================================
echo      SentinelFlow AI - Bootstrap Dev Environment Setup
echo ============================================================
powershell.exe -ExecutionPolicy Bypass -File "%~dp0..\..\setup.ps1"
if %ERRORLEVEL% neq 0 (
    echo.
    echo [-] Installation failed.
    pause
    exit /b 1
)
echo.
echo [+] Setup completed successfully.
pause
exit /b 0
