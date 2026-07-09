@echo off
title SentinelFlow AI - Reset Databases
echo ============================================================
echo          SentinelFlow AI - Database Reset & Seed
echo ============================================================

cd /d "%~dp0..\..\backend"
if exist "sentinelflow.db" (
    echo [*] Deleting existing sentinelflow.db file...
    del "sentinelflow.db"
    del "sentinelflow.db-shm" >nul 2>&1
    del "sentinelflow.db-wal" >nul 2>&1
    echo [+] Database files deleted.
)

if not exist "venv\Scripts\python.exe" (
    echo [-] Virtual environment not found. Please run setup first.
    pause
    exit /b 1
)

echo [*] Initializing clean schema and database configuration...
venv\Scripts\python.exe "%~dp0..\python\setup_databases.py"

echo [*] Generating mock incidents history data...
venv\Scripts\python.exe "%~dp0..\python\generate_incidents.py"

echo ============================================================
echo Database has been completely reset and seeded.
pause
