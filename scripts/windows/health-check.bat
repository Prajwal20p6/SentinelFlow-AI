@echo off
title SentinelFlow AI - Health Check
echo ============================================================
echo          SentinelFlow AI - Running Health Check
echo ============================================================

if exist "%~dp0..\..\backend\venv\Scripts\python.exe" (
    "%~dp0..\..\backend\venv\Scripts\python.exe" "%~dp0..\python\health_check.py"
) else (
    python "%~dp0..\python\health_check.py"
)

echo ============================================================
pause
