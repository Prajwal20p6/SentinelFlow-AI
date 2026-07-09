import pytest
import json
from fastapi.testclient import TestClient
from app.main import app
from app.models.models import Incident
from app.services.executive_service import calculate_business_impact, generate_executive_summary

@pytest.fixture
def auth_headers(db_session):
    from app.models.models import User
    from app.core.security import create_access_token
    user = db_session.query(User).filter(User.email == "admin@sentinelflow.ai").first()
    if not user:
        from app.core.security import hash_password
        user = User(
            full_name="Admin User",
            email="admin@sentinelflow.ai",
            hashed_password=hash_password("admin123"),
            role="admin",
            is_active=True,
            email_verified=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token(data={"sub": user.email, "role": user.role})
    return {"Authorization": f"Bearer {token}"}


def test_business_impact_calculations(db_session):
    # 1. Test standard performance incident
    incident_cpu = Incident(
        correlation_id="executive-impact-correlation-1",
        source="TelemetryMonitor",
        metric_type="CPU_SPIKE",
        severity="WARNING",
        title="CPU Anomaly",
        description="CPU spike alert on pod worker."
    )
    db_session.add(incident_cpu)
    db_session.commit()
    db_session.refresh(incident_cpu)

    impact_cpu = calculate_business_impact(incident_cpu)
    assert impact_cpu["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
    assert "SOC2" in impact_cpu["regulations_applicable"]
    assert impact_cpu["affected_users"] >= 100

    # 2. Test high priority security incident
    incident_sec = Incident(
        correlation_id="executive-impact-correlation-2",
        source="Ingress-Gateway",
        metric_type="UNAUTHORIZED_ACCESS",
        severity="CRITICAL",
        title="Unauthorized Security Probe",
        description="Malicious security scanning from host node."
    )
    db_session.add(incident_sec)
    db_session.commit()
    db_session.refresh(incident_sec)

    impact_sec = calculate_business_impact(incident_sec)
    assert impact_sec["risk_level"] == "CRITICAL"
    assert "GDPR" in impact_sec["regulations_applicable"]
    assert "PCI-DSS" in impact_sec["regulations_applicable"]
    assert len(impact_sec["required_notifications"]) >= 2


def test_executive_summary_generation_and_caching(db_session):
    incident = Incident(
        correlation_id="executive-summary-correlation-3",
        source="K8s Telemetry Monitor",
        metric_type="MEMORY_EXHAUSTION",
        severity="HIGH",
        title="High Memory Usage Alert",
        description="Core services warning memory limits exceeded on database pod.",
        suggested_action="kubectl rollout restart deployment/db-pod"
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    report = generate_executive_summary(db_session, incident)
    assert "summary" in report
    assert "business_impact" in report
    assert "compliance" in report

    # Verify db caching
    db_session.refresh(incident)
    assert incident.executive_report_json is not None
    cached_report = json.loads(incident.executive_report_json)
    assert cached_report["summary"] == report["summary"]


def test_executive_endpoints(db_session, auth_headers):
    incident = Incident(
        correlation_id="executive-endpoints-correlation-4",
        source="K8s Telemetry Monitor",
        metric_type="DISK_FULL",
        severity="WARNING",
        title="Disk capacity low alert",
        description="Storage claim low on PVC database disk.",
        suggested_action="kubectl exec -it db-pod -- find /tmp -mtime +7 -delete"
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    client = TestClient(app)

    # 1. Test executive report retrieval
    resp_report = client.get(
        f"/api/v1/incidents/{incident.id}/executive-report",
        headers=auth_headers
    )
    assert resp_report.status_code == 200
    report_data = resp_report.json()
    assert "summary" in report_data
    assert "business_impact" in report_data

    # 2. Test executive summary metrics
    resp_metrics = client.get(
        "/api/v1/agent/observability/executive/metrics",
        headers=auth_headers
    )
    assert resp_metrics.status_code == 200
    metrics_data = resp_metrics.json()
    assert "total_incidents" in metrics_data
    assert "mttd_seconds" in metrics_data
    assert "false_positive_rate" in metrics_data
