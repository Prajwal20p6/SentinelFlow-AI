"""
Pytest configuration and shared fixtures for SentinelFlow AI test suite.
Overrides settings to use a test database, mocks external integrations, and provides client/session fixtures.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure the backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import get_settings, Settings
from app.core.database import Base, get_db
import app.models.models as _unused_models_import
from app.main import app as fastapi_app

# ── Override Settings for Testing ────────────────────────────
TEST_DB_URL = "sqlite:///./test_sentinelflow.db"

@pytest.fixture(scope="session", autouse=True)
def override_settings():
    """Override application settings for the duration of the test suite."""
    settings = get_settings()
    
    # Save original settings
    orig_db = settings.DATABASE_URL
    orig_demo = settings.FF_DEMO_MODE
    orig_slack = settings.FF_SLACK_NOTIFICATIONS
    orig_mfa = settings.FF_MFA_REQUIRED
    orig_otel = settings.OTEL_ENABLED
    orig_secret = settings.SECRET_KEY
    
    # Apply test overrides
    settings.DATABASE_URL = TEST_DB_URL
    settings.ENVIRONMENT = "testing"
    settings.FF_DEMO_MODE = False
    settings.FF_SLACK_NOTIFICATIONS = False
    settings.FF_MFA_REQUIRED = False
    settings.OTEL_ENABLED = False
    settings.MASTRA_ENABLED = False
    settings.SECRET_KEY = "sentinelflow-test-secret-key-at-least-32-bytes-long"

    import app.core.database
    orig_engine = app.core.database.engine
    orig_session_local = app.core.database.SessionLocal

    test_engine_temp = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    app.core.database.engine = test_engine_temp
    app.core.database.SessionLocal = sessionmaker(bind=test_engine_temp)
    
    import app.main
    app.main.engine = test_engine_temp
    app.main.SessionLocal = app.core.database.SessionLocal
    
    # Ensure all tables are created on overridden engine
    Base.metadata.create_all(bind=test_engine_temp)
    
    yield settings
    
    # Restore original settings
    settings.DATABASE_URL = orig_db
    settings.FF_DEMO_MODE = orig_demo
    settings.FF_SLACK_NOTIFICATIONS = orig_slack
    settings.FF_MFA_REQUIRED = orig_mfa
    settings.OTEL_ENABLED = orig_otel

    app.core.database.engine = orig_engine
    app.core.database.SessionLocal = orig_session_local
    app.main.engine = orig_engine
    app.main.SessionLocal = orig_session_local


# ── Database Fixtures ─────────────────────────────────────────
@pytest.fixture(scope="session")
def test_engine():
    """Create a database engine specifically for testing."""
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Ensure all tables exist in the test DB
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Clean up the test database file
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("./test_sentinelflow.db"):
        try:
            os.remove("./test_sentinelflow.db")
        except PermissionError:
            pass


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Provides a clean transactional database session for each test case."""
    connection = test_engine.connect()
    transaction = connection.begin()
    
    Session = sessionmaker(bind=connection, expire_on_commit=False)
    session = Session()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function", autouse=True)
def override_db_dependency(db_session):
    """Overrides the FastAPI dependency get_db with the test session."""
    def _get_test_db():
        try:
            yield db_session
        finally:
            pass
            
    fastapi_app.dependency_overrides[get_db] = _get_test_db
    yield
    fastapi_app.dependency_overrides.pop(get_db, None)


# ── Client Fixture ────────────────────────────────────────────
@pytest.fixture(scope="function")
def client():
    """FastAPI TestClient fixture."""
    with TestClient(fastapi_app) as c:
        yield c
