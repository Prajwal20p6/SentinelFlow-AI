import pytest
from app.services.timeline_service import generate_decision_explanation, get_incident_timeline, reconstruct_incident_forensics
from app.models.models import Incident, TimelineEvent, User
from app.core.security import hash_password

@pytest.fixture
def test_user_headers(client, db_session):
    user = db_session.query(User).filter(User.email == "auditor@sentinelflow.ai").first()
    if not user:
        user = User(
            email="auditor@sentinelflow.ai",
            hashed_password=hash_password("auditorpass"),
            full_name="Forensic Auditor",
            role="engineer",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    
    resp = client.post("/api/v1/auth/login", json={
        "email": "auditor@sentinelflow.ai",
        "password": "auditorpass"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_explainability_markdown_generation():
    reasoning_explanation = generate_decision_explanation("LLM_REASONING", {
        "provider": "OpenAI GPT-4",
        "confidence": 0.85,
        "contradictions": "None",
        "reasoning": "Standard CPU spike due to request overload.",
        "remediation_plan": "kubectl scale deployment/api-gateway --replicas=3"
    })
    assert "### AI Reasoner & Diagnosis Explanation" in reasoning_explanation
    assert "OpenAI GPT-4" in reasoning_explanation
    assert "0.85" in reasoning_explanation
    assert "deployment/api-gateway" in reasoning_explanation

    safety_explanation = generate_decision_explanation("SAFETY_CHECK", {
        "status": "BLOCKED",
        "risk_score": 0.99,
        "assessment": "Forced file deletion matched policies.",
        "command": "rm -rf /"
    })
    assert "### Safety Envelope Evaluation" in safety_explanation
    assert "BLOCKED" in safety_explanation
    assert "rm -rf /" in safety_explanation

def test_timeline_and_forensics_endpoints(client, db_session, test_user_headers):
    # 1. Create a dummy incident
    incident = Incident(
        title="Forensic Test Incident",
        source="k8s",
        metric_type="CPU_SPIKE",
        severity="high",
        status="DETECTED",
        description="Kubernetes node CPU high",
        correlation_id="forensic-cid-111"
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    # 2. Add some timeline events
    event1 = TimelineEvent(
        incident_id=incident.id,
        event_type="DETECTED",
        title="Anomaly Ingested",
        description="CPU Spike detected",
        actor="system",
        decision_rationale="Ingested anomaly correlation id forensic-cid-111."
    )
    db_session.add(event1)
    db_session.commit()

    # 3. Test timeline endpoint
    resp = client.get(f"/api/v1/incidents/{incident.id}/timeline", headers=test_user_headers)
    assert resp.status_code == 200
    timeline = resp.json()
    assert len(timeline) == 1
    assert timeline[0]["event_type"] == "DETECTED"
    assert "forensic-cid-111" in timeline[0]["decision_rationale"]

    # 4. Test forensics endpoint with explainability report
    import json
    incident.explainability_json = json.dumps({
        "rca": {"confidence_score": 90, "why_conclusion": "Pattern matched"},
        "overall_explanation": "Test explanation string"
    })
    db_session.commit()

    resp_f = client.get(f"/api/v1/incidents/{incident.id}/forensics", headers=test_user_headers)
    assert resp_f.status_code == 200
    forensics = resp_f.json()
    assert forensics["incident_id"] == incident.id
    assert len(forensics["timeline"]) == 1
    assert forensics["correlation_id"] == "forensic-cid-111"
    assert forensics["explainability_report"] is not None
    assert forensics["explainability_report"]["overall_explanation"] == "Test explanation string"
    assert forensics["explainability_report"]["rca"]["confidence_score"] == 90
