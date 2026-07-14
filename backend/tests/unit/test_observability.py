import pytest
from prometheus_client import generate_latest
from app.core.observability import METRIC_REGISTRY, track_incident_created, track_workflow_step, track_llm_request

def test_health_check_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

def test_readiness_check_endpoint(client):
    resp = client.get("/api/v1/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"
    assert resp.json()["dependencies"]["database"] == "OK"

def test_prometheus_metrics_endpoint(client):
    # Trigger some metrics tracking
    track_incident_created("critical", "DETECTED", "CPU_SPIKE")
    track_workflow_step("PLAN_REMEDIATION", "completed", 1.25)
    track_llm_request("simulation", "success", 0.85)

    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    metrics_data = resp.text
    
    assert "sf_incidents_total" in metrics_data
    assert "sf_workflow_step_latency_seconds" in metrics_data
    assert "sf_llm_calls_total" in metrics_data
    assert "sf_llm_duration_seconds" in metrics_data
