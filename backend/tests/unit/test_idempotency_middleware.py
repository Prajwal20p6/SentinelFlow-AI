import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.middleware.idempotency_middleware import IdempotencyMiddleware
from app.services.idempotency_service import IdempotencyService
from app.models.models import IdempotencyKey
from app.core.config import get_settings


@pytest.fixture(autouse=True)
def override_session_local(db_session):
    """Ensure IdempotencyMiddleware uses the pytest db_session fixture."""
    with patch("app.middleware.idempotency_middleware.SessionLocal", side_effect=lambda: db_session):
        yield


def create_idempotency_test_app():

    app = FastAPI()
    app.add_middleware(IdempotencyMiddleware)

    @app.post("/execute-command")
    async def sample_execute(request: Request):
        body = await request.json()
        if body.get("fail"):
            raise ValueError("Downstream execution failed")
        if body.get("error_code"):
            return JSONResponse(status_code=body.get("error_code"), content={"detail": "Bad request error"})
        if body.get("invalid_json_response"):
            from starlette.responses import Response
            return Response(content=b"{invalid_json", media_type="application/json", status_code=200)
        return {"status": "SUCCESS", "command": body.get("command", "ls")}

    return app


def test_unprotected_route_bypasses_middleware():
    """GET requests and unprotected paths should bypass idempotency checks."""
    app = create_idempotency_test_app()
    
    @app.get("/unprotected")
    def unprotected():
        return {"status": "ok"}
        
    client = TestClient(app)
    resp = client.get("/unprotected")
    assert resp.status_code == 200


def test_missing_idempotency_key_production_environment():
    """In production mode, missing idempotency key on protected path returns 400."""
    settings = get_settings()
    orig_env = settings.ENVIRONMENT
    try:
        settings.ENVIRONMENT = "production"
        app = create_idempotency_test_app()
        client = TestClient(app)

        resp = client.post("/execute-command", json={"command": "ls"})
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Missing Idempotency-Key header"
    finally:
        settings.ENVIRONMENT = orig_env


def test_idempotency_processing_status_returns_409(db_session):
    """When a request with idempotency key is currently processing (status 202), returns 409 Conflict."""
    key = "idem-proc-key-99"
    IdempotencyService.register_key(db_session, key, action_type="/execute-command")
    db_session.commit()

    settings = get_settings()
    orig_env = settings.ENVIRONMENT
    try:
        settings.ENVIRONMENT = "production"
        app = create_idempotency_test_app()
        client = TestClient(app)

        resp = client.post("/execute-command", json={"command": "ls"}, headers={"idempotency-key": key})
        assert resp.status_code == 409
        assert "already in progress" in resp.json()["detail"]
    finally:
        settings.ENVIRONMENT = orig_env


def test_idempotency_cached_response_hit(db_session):
    """When a response is cached for an idempotency key, returns cached response directly."""
    key = "idem-cached-key-100"
    IdempotencyService.register_key(db_session, key, action_type="/execute-command")
    IdempotencyService.save_response(db_session, key, status_code=200, body={"status": "CACHED_OK"})
    db_session.commit()

    settings = get_settings()
    orig_env = settings.ENVIRONMENT
    try:
        settings.ENVIRONMENT = "production"
        app = create_idempotency_test_app()
        client = TestClient(app)

        resp = client.post("/execute-command", json={"command": "ls"}, headers={"idempotency-key": key})
        assert resp.status_code == 200
        assert resp.json() == {"status": "CACHED_OK"}
    finally:
        settings.ENVIRONMENT = orig_env



def test_idempotency_duplicate_concurrent_registration_failure(db_session):
    """If key registration fails due to race condition, middleware returns 409."""
    key = "idem-race-key-101"

    settings = get_settings()
    orig_env = settings.ENVIRONMENT
    try:
        settings.ENVIRONMENT = "production"
        app = create_idempotency_test_app()
        client = TestClient(app)

        with patch("app.services.idempotency_service.IdempotencyService.register_key", return_value=False):
            resp = client.post("/execute-command", json={"command": "ls"}, headers={"idempotency-key": key})
            assert resp.status_code == 409
            assert "Duplicate or concurrent request detected" in resp.json()["detail"]
    finally:
        settings.ENVIRONMENT = orig_env


def test_idempotency_clears_key_on_downstream_exception(db_session):
    """When downstream handler raises an exception, the idempotency key is deleted so retry succeeds."""
    key = "idem-exception-key-102"

    settings = get_settings()
    orig_env = settings.ENVIRONMENT
    try:
        settings.ENVIRONMENT = "production"
        app = create_idempotency_test_app()
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post("/execute-command", json={"fail": True}, headers={"idempotency-key": key})
        assert resp.status_code == 500

        # Verify key was deleted so client can retry
        cached = IdempotencyService.get_cached_response(db_session, key)
        assert cached is None
    finally:
        settings.ENVIRONMENT = orig_env


def test_idempotency_clears_key_on_error_status_code(db_session):
    """When downstream handler returns HTTP >= 400 error status, key is deleted allowing client retry."""
    key = "idem-error-status-key-103"

    settings = get_settings()
    orig_env = settings.ENVIRONMENT
    try:
        settings.ENVIRONMENT = "production"
        app = create_idempotency_test_app()
        client = TestClient(app)

        resp = client.post("/execute-command", json={"error_code": 400}, headers={"idempotency-key": key})
        assert resp.status_code == 400

        # Key should be deleted for error status codes
        cached = IdempotencyService.get_cached_response(db_session, key)
        assert cached is None
    finally:
        settings.ENVIRONMENT = orig_env


def test_idempotency_handles_invalid_json_body_gracefully(db_session):
    """If downstream returns unparseable JSON, middleware handles parse error gracefully without crashing."""
    key = "idem-invalid-json-key-104"

    settings = get_settings()
    orig_env = settings.ENVIRONMENT
    try:
        settings.ENVIRONMENT = "production"
        app = create_idempotency_test_app()
        client = TestClient(app)

        resp = client.post("/execute-command", json={"invalid_json_response": True}, headers={"idempotency-key": key})
        assert resp.status_code == 200
        assert resp.text == "{invalid_json"
    finally:
        settings.ENVIRONMENT = orig_env
