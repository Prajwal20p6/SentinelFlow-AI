@echo off
title SentinelFlow AI - Backend Server
echo ============================================================
echo          SentinelFlow AI - Starting Backend Server
echo ============================================================
cd /d "%~dp0..\..\backend"
if not exist "venv\Scripts\python.exe" (
    echo [-] Virtual environment not found. Please run setup first.
    pause
    exit /b 1
)
venv\Scripts\python.exe run.py
