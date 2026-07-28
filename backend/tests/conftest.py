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
def override_settings(tmp_path_factory):
    """Override application settings for the duration of the test suite."""
    settings = get_settings()
    
    # Save original settings
    orig_db = settings.DATABASE_URL
    orig_demo = settings.FF_DEMO_MODE
    orig_slack = settings.FF_SLACK_NOTIFICATIONS
    orig_mfa = settings.FF_MFA_REQUIRED
    orig_otel = settings.OTEL_ENABLED
    orig_secret = settings.SECRET_KEY
    orig_qdrant_path = settings.QDRANT_PATH
    
    # Create isolated per-test-session directory for Qdrant/vector storage
    qdrant_test_dir = tmp_path_factory.mktemp("qdrant_test_data")
    
    # Apply test overrides
    settings.DATABASE_URL = TEST_DB_URL
    settings.ENVIRONMENT = "testing"
    settings.FF_DEMO_MODE = False
    settings.FF_SLACK_NOTIFICATIONS = False
    settings.FF_MFA_REQUIRED = False
    settings.OTEL_ENABLED = False
    settings.MASTRA_ENABLED = False
    settings.ENKRYPTAI_ENABLED = False
    settings.SECRET_KEY = "sentinelflow-test-secret-key-at-least-32-bytes-long"
    settings.QDRANT_PATH = str(qdrant_test_dir)

    # Reset any cached vector DB client instances so they lazily initialize using test QDRANT_PATH
    try:
        import app.core.vector_db as vdb
        if hasattr(vdb, "reset_qdrant_client"):
            vdb.reset_qdrant_client()
    except Exception:
        pass

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
    settings.QDRANT_PATH = orig_qdrant_path

    app.core.database.engine = orig_engine
    app.core.database.SessionLocal = orig_session_local
    app.main.engine = orig_engine
    app.main.SessionLocal = orig_session_local

    # Flush and shutdown OpenTelemetry tracer provider before pytest closes stdout/stderr
    try:
        from opentelemetry import trace
        provider = trace.get_tracer_provider()
        if hasattr(provider, "shutdown"):
            provider.shutdown()
    except Exception:
        pass


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


# ── External Network Guard Fixture ────────────────────────────
@pytest.fixture(scope="function", autouse=True)
def mock_external_network_dependencies(monkeypatch):
    """
    Autouse fixture that blocks any external network socket calls to Qdrant,
    Enkrypt AI, or LLM APIs (OpenAI / Anthropic) during pytest execution.
    Only local loopback connections (127.0.0.1 / localhost) are permitted.
    """
    import socket
    orig_connect = socket.socket.connect

    def guarded_connect(self, address):
        host = address[0] if isinstance(address, tuple) and len(address) > 0 else str(address)
        if host in ("127.0.0.1", "localhost", "0.0.0.0", "::1"):
            return orig_connect(self, address)
        raise RuntimeError(f"External network call blocked during tests: attempted connection to {host}")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)

