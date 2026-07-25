import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.main import app
from app.api.router_ops import router as ops_router
from app.core.observability import METRIC_REGISTRY, track_incident_created, track_workflow_step, track_llm_request

def test_health_check_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

def test_readiness_check_endpoint():
    test_app = FastAPI()
    test_app.include_router(ops_router, prefix="/api/v1/ops")
    
    mock_db = MagicMock()
    test_app.dependency_overrides = {}
    from app.core.database import get_db
    test_app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.core.vector_db.qdrant_client", MagicMock()):
        c = TestClient(test_app)
        resp = c.get("/api/v1/ops/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"
        assert resp.json()["dependencies"]["database"] == "OK"

def test_prometheus_metrics_endpoint():
    test_app = FastAPI()
    test_app.include_router(ops_router, prefix="/api/v1/ops")
    c = TestClient(test_app)

    # Trigger some metrics tracking
    track_incident_created("critical", "DETECTED", "CPU_SPIKE")
    track_workflow_step("PLAN_REMEDIATION", "completed", 1.25)
    track_llm_request("simulation", "success", 0.85)

    resp = c.get("/api/v1/ops/metrics")
    assert resp.status_code == 200
    metrics_data = resp.text

    assert "sf_incidents_total" in metrics_data
    assert "sf_workflow_step_latency_seconds" in metrics_data
    assert "sf_llm_calls_total" in metrics_data
    assert "sf_llm_duration_seconds" in metrics_data
