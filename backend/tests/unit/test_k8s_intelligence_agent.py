import pytest
import json
from app.models.models import Incident, TimelineEvent
from app.services.k8s_intelligence_agent import run_k8s_intelligence_analysis

def test_k8s_intelligence_analysis_cpu_spike(db_session):
    # 1. Create a dummy incident with CPU spike
    incident = Incident(
        correlation_id="test-k8s-corr-01",
        source="Kubernetes",
        metric_type="CPU_SPIKE",
        severity="CRITICAL",
        title="pod-api-gateway-123456",
        description="CPU utilization exceeded threshold of 90% continuously.",
        status="DETECTED"
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    # 2. Run analysis
    res = run_k8s_intelligence_analysis(db_session, incident.id)
    
    # 3. Assert results
    assert "issue" in res
    assert res["severity"] == "high"
    assert "remediation_action" not in res  # It should be inside suggested_remediation list
    assert len(res["suggested_remediation"]) > 0
    assert "rollback_plan" in res
    assert "best_practice_checks" in res
    assert res["best_practice_checks"]["resource_limits_configured"] is True

    # Check database persistence
    db_session.refresh(incident)
    assert incident.k8s_analysis_json is not None
    saved_data = json.loads(incident.k8s_analysis_json)
    assert saved_data["issue"] == res["issue"]

    # Check timeline events
    events = db_session.query(TimelineEvent).filter(
        TimelineEvent.incident_id == incident.id,
        TimelineEvent.event_type == "K8S_ANALYSIS"
    ).all()
    assert len(events) == 1
    assert events[0].source_system == "Kubernetes"
    assert events[0].event_severity == "HIGH"


def test_k8s_intelligence_analysis_disk_full(db_session):
    # 1. Create a dummy incident with Disk issues
    incident = Incident(
        correlation_id="test-k8s-corr-02",
        source="Kubernetes",
        metric_type="DISK_FULL",
        severity="WARNING",
        title="node-infrastructure-03",
        description="Host persistent volume PVC is out of disk partition space.",
        status="DETECTED"
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    # 2. Run analysis
    res = run_k8s_intelligence_analysis(db_session, incident.id)

    # 3. Assert disk-specific parameters
    assert res["severity"] == "critical"
    assert "DiskPressure" in res["issue"] or "Disk" in res["issue"]
    assert res["best_practice_checks"]["health_checks_configured"] is False

    # Check timeline event severity is recorded as CRITICAL (matching agent result upper)
    event = db_session.query(TimelineEvent).filter(
        TimelineEvent.incident_id == incident.id,
        TimelineEvent.event_type == "K8S_ANALYSIS"
    ).first()
    assert event is not None
    assert event.event_severity == "CRITICAL"
