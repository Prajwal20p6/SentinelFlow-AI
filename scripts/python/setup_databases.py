"""
SentinelFlow AI — Database Setup & Seeding Helper Script
Initializes SQLAlchemy database tables and seeds standard users and templates.
"""

import os
import sys
from alembic.config import Config
from alembic import command

# Ensure backend directory is in python path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, backend_path)

try:
    from app.core.database import SessionLocal
    from app.services.workflow_service import seed_prompt_templates
    from app.services.auth_service import seed_default_users
except ImportError as e:
    print(f"[-] Import error: {e}")
    print("[-] Please run this script using the backend virtual environment python.")
    sys.exit(1)

def main():
    print("="*60)
    print("      SENTINELFLOW AI - DATABASE BOOTSTRAP SYSTEM")
    print("="*60)
    
    print("[*] Creating database schema tables via Alembic migrations...")
    try:
        # Load the Alembic configuration and run migrations programmatically
        alembic_ini_path = os.path.join(backend_path, "alembic.ini")
        alembic_cfg = Config(alembic_ini_path)
        
        # Explicitly configure script_location to be an absolute path
        alembic_cfg.set_main_option("script_location", os.path.join(backend_path, "alembic"))
        
        command.upgrade(alembic_cfg, "head")
        print("[+] Schema tables and migrations applied successfully.")
    except Exception as e:
        print(f"[-] Failed to initialize database: {e}")
        sys.exit(1)
        
    print("[*] Seeding database configurations...")
    db = SessionLocal()
    try:
        seed_prompt_templates(db)
        seed_default_users(db)
        print("[+] Database seeding completed successfully.")
    except Exception as e:
        print(f"[-] Database seeding failed: {e}")
        db.rollback()
    finally:
        db.close()
        
    print("="*60)
    print("         DATABASE BOOTSTRAP COMPLETED SUCCESSFULLY")
    print("="*60)

if __name__ == "__main__":
    main()
