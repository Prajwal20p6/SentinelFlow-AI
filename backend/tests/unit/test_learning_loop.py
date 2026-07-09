import pytest
import json
from fastapi.testclient import TestClient
from app.main import app
from app.models.models import Incident, TimelineEvent, RecommendationFeedback, MastraWorkflowState, IncidentLog
from app.services.memory_service import search_similar_resolved_incidents, retrieve_memory
from app.services.incident_service import update_incident_status
from app.services.workflow_service import run_incident_workflow

@pytest.fixture
def auth_headers(db_session):
    # Retrieve test client headers with authorization
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


def test_learning_loop_feedback_submission(db_session, auth_headers):
    # 1. Create a test incident
    incident = Incident(
        correlation_id="learning-feedback-correlation-1",
        source="TelemetrySource",
        metric_type="CPU_SPIKE",
        severity="WARNING",
        title="Spiking CPU warning",
        description="CPU reached 94% on api pod.",
        suggested_action="kubectl restart pod/api-pod",
        status="ANALYZING"
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    client = TestClient(app)

    # 2. Submit correction feedback
    feedback_payload = {
        "original_recommendation": "kubectl restart pod/api-pod",
        "engineer_correction": "kubectl scale deployment/api-deploy --replicas=3",
        "reasoning": "Scale out deployment replicas instead of just restarting a single pod to distribute load."
    }
    
    resp = client.post(
        f"/api/v1/incidents/{incident.id}/feedback",
        json=feedback_payload,
        headers=auth_headers
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["engineer_correction"] == "kubectl scale deployment/api-deploy --replicas=3"

    # 3. Assert incident suggested action is overridden
    db_session.refresh(incident)
    assert incident.suggested_action == "kubectl scale deployment/api-deploy --replicas=3"

    # 4. Assert timeline event is added
    evt = db_session.query(TimelineEvent).filter(
        TimelineEvent.incident_id == incident.id,
        TimelineEvent.event_type == "RECOMMENDATION_CORRECTED"
    ).first()
    assert evt is not None
    assert "AI suggested action corrected" in evt.title


def test_org_memory_sync_and_retrieval(db_session):
    # 1. Create and resolve an incident (transitioning to EXECUTED)
    incident = Incident(
        correlation_id="learning-org-mem-correlation-2",
        source="LogSource",
        metric_type="MEMORY_EXHAUSTION",
        severity="CRITICAL",
        title="High Memory Usage Alert",
        description="Core services warning memory limits exceeded on app-service.",
        suggested_action="kubectl rollout restart deployment/app-service",
        status="ANALYZING"
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    # Resolve incident
    update_incident_status(db_session, incident.id, "BYPASSED", actor="admin")
    update_incident_status(db_session, incident.id, "EXECUTED", actor="admin")
    
    # 2. Query org_memory vector search to retrieve it
    past_resolved = search_similar_resolved_incidents("memory limits exceeded", limit=1)
    assert len(past_resolved) >= 1
    
    match = next((p for p in past_resolved if p["incident_id"] == incident.id), None)
    assert match is not None
    assert match["outcome"] == "EXECUTED"
    assert match["metric_type"] == "MEMORY_EXHAUSTION"


def test_workflow_learning_prompts_injection(db_session):
    # Pre-seed a feedback entry for CPU_SPIKE to verify injection
    incident_old = Incident(
        correlation_id="preseed-feedback-correlation",
        source="LogSource",
        metric_type="CPU_SPIKE",
        severity="HIGH",
        title="Preseeded high CPU spike",
        description="CPU spike alert on pod gateway.",
        status="ANALYZING"
    )
    db_session.add(incident_old)
    db_session.commit()
    
    from app.models.models import RecommendationFeedback
    fb = RecommendationFeedback(
        incident_id=incident_old.id,
        original_recommendation="kubectl restart pod/gateway",
        engineer_correction="kubectl scale deployment/gateway --replicas=5",
        reasoning="Preseeded manual scale fix."
    )
    db_session.add(fb)
    db_session.commit()

    # Seed Mastra workflow state to resume
    correlation_id = "test-learning-workflow-correlation"
    incident_new = Incident(
        correlation_id=correlation_id,
        source="Telemetry",
        metric_type="CPU_SPIKE",
        severity="HIGH",
        title="New CPU Alert",
        description="CPU spike detected on production gateway.",
        status="ANALYZING",
        root_cause_json='{"analysis": "mock rca"}'
    )
    db_session.add(incident_new)
    db_session.commit()

    wf_state = MastraWorkflowState(
        workflow_name="incident_response",
        correlation_id=correlation_id,
        current_state="RETRIEVE_CONTEXT",
        context_data_json=json.dumps({"incident_id": incident_new.id}),
        is_completed=False
    )
    db_session.add(wf_state)
    db_session.commit()

    # Run SRE reasoning workflow
    run_incident_workflow(
        db=db_session,
        anomaly_type=incident_new.metric_type,
        description=incident_new.description,
        severity=incident_new.severity,
        node_name="node-01",
        correlation_id=correlation_id
    )

    # Assert reasoning log is added
    logs = db_session.query(IncidentLog).filter(
        IncidentLog.incident_id == incident_new.id,
        IncidentLog.stage == "REASONING"
    ).all()
    assert len(logs) >= 1


def test_admin_feedback_observability_metrics(db_session, auth_headers):
    client = TestClient(app)
    resp = client.get(
        "/api/v1/agent/observability/feedback",
        headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "metrics" in data
    assert "acceptance_rate_percent" in data["metrics"]
    assert "total_feedback_count" in data["metrics"]
