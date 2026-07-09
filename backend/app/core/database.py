"""
SentinelFlow AI — Database Engine & Session Management
Supports PostgreSQL (production) and SQLite (development/demo) with automatic fallback.
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator

from .config import get_settings

settings = get_settings()

# ── Engine Configuration ─────────────────────────────────────
connect_args = {}
if settings.is_sqlite:
    connect_args["check_same_thread"] = False

engine_kwargs = {
    "connect_args": connect_args,
    "echo": settings.DEBUG and settings.ENVIRONMENT == "development",
    "pool_pre_ping": True,
}
if not settings.is_sqlite:
    engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW
    engine_kwargs["pool_timeout"] = settings.DATABASE_POOL_TIMEOUT

engine = create_engine(
    settings.get_database_url,
    **engine_kwargs
)

# Enable WAL mode for SQLite concurrent access
if settings.is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# ── Session Factory ──────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Declarative Base ─────────────────────────────────────────
class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""
    pass


# ── Dependency Injection ─────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Used for development/demo mode."""
    Base.metadata.create_all(bind=engine)
