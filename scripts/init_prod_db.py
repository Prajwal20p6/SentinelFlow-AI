"""
SentinelFlow AI — Production Database Initialization & Verification Script
Initializes PostgreSQL tables via Base.metadata.create_all() and seeds default data.
"""
import sys
import os
from pathlib import Path

# Add backend to python path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy import inspect
from app.core.config import get_settings
from app.core.database import init_db, engine
from app.services.auth_service import seed_default_users
from app.services.workflow_service import seed_prompt_templates
from app.services.policy_engine import PolicyEngine
from app.core.database import SessionLocal
from app.models.models import ExecutionConfig, User

def main():
    settings = get_settings()
    masked_url = settings.DATABASE_URL
    if "@" in masked_url:
        prefix, rest = masked_url.split("@", 1)
        scheme = prefix.split("://")[0]
        masked_url = f"{scheme}://****:****@{rest}"
    
    print(f"Connecting to production database: {masked_url}")
    
    # 1. Test database connection & create schema
    try:
        init_db()
        print("Database schema initialized successfully (create_all executed).")
    except Exception as e:
        print(f"Database connection/schema creation failed: {e}")
        sys.exit(1)

    # 2. Seed default data
    db = SessionLocal()
    try:
        seed_default_users(db)
        seed_prompt_templates(db)
        PolicyEngine.seed_default_policies(db)
        if not db.query(ExecutionConfig).first():
            config = ExecutionConfig(
                id=1,
                mode="MANUAL",
                rate_limit_per_minute=5,
                min_confidence_score=90,
                max_blast_radius=10,
                restricted_services="payment",
                low_risk_actions="restart_pod,scale_service,rollout_restart"
            )
            db.add(config)
            db.commit()
        print("Default production seed data inserted successfully.")
    except Exception as e:
        print(f"Warning during seed insertion: {e}")
    finally:
        db.close()

    # 3. Verify created tables
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print("\n============================================================")
    print("   === VERIFIED PRODUCTION DATABASE TABLES ===")
    print("============================================================")
    for idx, table in enumerate(sorted(tables), 1):
        print(f"  {idx:2d}. {table}")
    print(f"\nTotal Tables Created: {len(tables)}")
    print("============================================================")

    # 4. Verify Admin Seed User
    db2 = SessionLocal()
    try:
        admin_user = db2.query(User).filter(User.email == "admin@sentinelflow.ai").first()
        if admin_user:
            print(f"\nDefault Admin User Verified: {admin_user.email} (Role: {admin_user.role}, ID: {admin_user.id})")
        else:
            print("\nAdmin user not found in database!")
    finally:
        db2.close()

if __name__ == "__main__":
    main()
