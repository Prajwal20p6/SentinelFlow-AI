import pytest
from app.services.prioritization_agent import IncidentPrioritizationAgent
from app.services.simulation_service import SimulationEngine
from app.services.remediation_agent import RemediationAgent
from app.services.decision_graph_service import DecisionGraphService
from app.services.runbook_recommendation_service import RunbookRecommendationService
from app.services.replay_service import IncidentReplayEngine
from app.models.models import Incident, User
from app.core.security import hash_password

@pytest.fixture
def auth_headers(client, db_session):
    user = db_session.query(User).filter(User.email == "responder@sentinelflow.ai").first()
    if not user:
        user = User(
            email="responder@sentinelflow.ai",
            hashed_password=hash_password("responderpass"),
            full_name="Incident Responder",
            role="engineer",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    resp = client.post("/api/v1/auth/login", json={
        "email": "responder@sentinelflow.ai",
        "password": "responderpass"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_prioritization_calculations():
    res = IncidentPrioritizationAgent.calculate_priority(
        metric_type="CPU_SPIKE",
        severity="HIGH",
        description="CPU Spike detected in auth-service, thousands of clients impacted"
    )
    assert res["score"] > 50
    assert "P" in res["sla_target"]
    assert res["sla_breach_at"] is not None

def test_simulation_engine_estimates():
    res = SimulationEngine.simulate("kubectl rollout restart deployment/payment-gateway")
    assert res["remediation_type"] == "DEPLOYMENT_RESTART"
    assert res["rollback_possible"] is True
    assert res["success_probability"] == 95.0

def test_remediation_ranking_scores():
    agent = RemediationAgent()
    options = agent.rank_options("MEMORY_EXHAUSTION", "payment-gateway-9f7d2e4a1", "payment-gateway")
    assert len(options) == 3
    # First option should have highest score
    assert options[0]["composite_score"] >= options[1]["composite_score"]

def test_decision_graph_dag_generation(db_session):
    incident = Incident(
        correlation_id="test-dag-cid-111",
        source="auth-service",
        metric_type="CPU_SPIKE",
        severity="WARNING",
        title="Auth service delay",
        description="Authorization service is slow",
        status="PENDING_APPROVAL",
        confidence_score=0.85,
        suggested_action="kubectl rollout restart deployment/auth-service"
    )
    db_session.add(incident)
    db_session.commit()

    graph = DecisionGraphService.build_graph(incident, db_session)
    assert len(graph["nodes"]) > 4
    assert len(graph["edges"]) > 4
    assert any(n["id"] == "alert_node" for n in graph["nodes"])

def test_runbook_recommendations():
    recs = RunbookRecommendationService.get_recommendations("MEMORY_EXHAUSTION", "oom leak", "CRITICAL")
    assert len(recs) == 2
    assert recs[0]["id"] == "rb_mem_leak"
    assert recs[0]["score"] == 94.6

def test_replay_mode_seeding(client, db_session, auth_headers):
    incident = Incident(
        correlation_id="test-replay-cid-222",
        source="payment-gateway",
        metric_type="MEMORY_EXHAUSTION",
        severity="CRITICAL",
        title="Payment gateway memory leak",
        description="Out of memory errors",
        status="DETECTED",
        confidence_score=0.90,
        suggested_action="kubectl scale deployment payment-gateway --replicas=3"
    )
    db_session.add(incident)
    db_session.commit()

    resp = client.get(f"/api/v1/incidents/{incident.id}/replay", headers=auth_headers)
    assert resp.status_code == 200
    replay = resp.json()
    assert len(replay) == 11
    assert replay[0]["event_type"] == "ALERT_RECEIVED"
    assert "Incident Declared" in replay[1]["decision"]
