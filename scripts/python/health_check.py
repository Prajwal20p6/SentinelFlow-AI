"""
SentinelFlow AI — Cross-Platform System Health Check Script
Verifies runtime dependencies, local databases, and service endpoint status.
"""

import sys
import os
import urllib.request
import urllib.error
import sqlite3

def check_python_version():
    print(f"[*] Python Version: {sys.version}")
    if sys.version_info < (3, 11):
        print("[!] Warning: Recommended Python version is 3.11+")
        return False
    print("[+] Python version is compatible.")
    return True

def check_local_database():
    db_path = os.path.join(os.path.dirname(__file__), "..", "..", "backend", "sentinelflow.db")
    print(f"[*] Checking Database File: {os.path.abspath(db_path)}")
    if not os.path.exists(db_path):
        print("[-] Database file not found. Database setup may be needed.")
        return False
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cursor.fetchall()]
        conn.close()
        print(f"[+] Connected to database. Found {len(tables)} tables: {', '.join(tables)}")
        return True
    except Exception as e:
        print(f"[-] Database query failed: {e}")
        return False

def check_service(url, name):
    print(f"[*] Verifying Service: {name} ({url})")
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.getcode() in (200, 404): # 404 is still alive
                print(f"[+] Service {name} is active. Response code: {resp.getcode()}")
                return True
    except urllib.error.URLError as e:
        print(f"[-] Service {name} is unreachable. Error: {e.reason}")
    except Exception as e:
        print(f"[-] Service {name} verify failed: {e}")
    return False

def main():
    print("="*60)
    print("      SENTINELFLOW AI - ENVIRONMENT HEALTH DIAGNOSTIC")
    print("="*60)
    
    py_ok = check_python_version()
    print("-" * 60)
    db_ok = check_local_database()
    print("-" * 60)
    
    # Check running services
    backend_ok = check_service("http://127.0.0.1:8000/api/v1/telemetry/metrics", "FastAPI Backend")
    frontend_ok = check_service("http://localhost:3000", "Next.js Frontend")
    
    print("=" * 60)
    print("                     DIAGNOSTIC SUMMARY")
    print("=" * 60)
    print(f"  Python Runtime:      {'OK' if py_ok else 'WARN'}")
    print(f"  Local SQLite Database: {'OK' if db_ok else 'FAILED/NOT SETUP'}")
    print(f"  FastAPI Backend:     {'ONLINE' if backend_ok else 'OFFLINE'}")
    print(f"  Next.js Frontend:    {'ONLINE' if frontend_ok else 'OFFLINE'}")
    print("=" * 60)

if __name__ == "__main__":
    main()
