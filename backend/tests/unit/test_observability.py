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


def test_observability_service_summary(db_session):
    """Test get_observability_summary calculation with empty and populated database."""
    from app.services.observability_service import get_observability_summary, get_recent_traces
    from app.models.models import AIObservabilityTrace

    # 1. Empty DB summary
    summary_empty = get_observability_summary(db_session)
    assert summary_empty["total_traces"] >= 0
    assert "avg_latency_ms" in summary_empty
    assert "traces_by_step" in summary_empty

    # 2. Seed traces
    t1 = AIObservabilityTrace(
        correlation_id="obs-cid-1",
        step_name="ROOT_CAUSE_ANALYSIS",
        input_tokens=100,
        output_tokens=50,
        latency_ms=120.5,
        status="success"
    )
    t2 = AIObservabilityTrace(
        correlation_id="obs-cid-1",
        step_name="ROOT_CAUSE_ANALYSIS",
        input_tokens=200,
        output_tokens=80,
        latency_ms=300.0,
        status="error"
    )
    db_session.add(t1)
    db_session.add(t2)
    db_session.commit()

    summary_populated = get_observability_summary(db_session)
    assert summary_populated["total_traces"] >= 2
    assert summary_populated["error_count"] >= 1
    assert summary_populated["total_input_tokens"] >= 300
    assert summary_populated["total_output_tokens"] >= 130
    assert "ROOT_CAUSE_ANALYSIS" in summary_populated["traces_by_step"]


def test_observability_service_recent_traces(db_session):
    """Test get_recent_traces querying with and without correlation_id filter."""
    from app.services.observability_service import get_recent_traces
    from app.models.models import AIObservabilityTrace

    cid = "obs-filter-cid-999"
    t = AIObservabilityTrace(
        correlation_id=cid,
        step_name="SAFETY_GUARDRAIL",
        input_tokens=50,
        output_tokens=10,
        latency_ms=15.0,
        status="success"
    )
    db_session.add(t)
    db_session.commit()

    all_traces = get_recent_traces(db_session, limit=10)
    assert len(all_traces) > 0

    filtered_traces = get_recent_traces(db_session, limit=10, correlation_id=cid)
    assert len(filtered_traces) == 1
    assert filtered_traces[0].correlation_id == cid

