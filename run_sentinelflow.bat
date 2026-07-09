@echo off
title SentinelFlow AI Launcher
echo ============================================================
echo           SentinelFlow AI - Launching Platform
echo ============================================================
powershell.exe -ExecutionPolicy Bypass -File "%~dp0start-sentinelflow.ps1"
if %ERRORLEVEL% neq 0 (
    echo.
    echo Launch failed. Please make sure setup.ps1 has been run successfully.
    pause
)
