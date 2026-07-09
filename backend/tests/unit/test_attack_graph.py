import pytest
from app.services.attack_graph_service import AttackGraphService

def test_generate_attack_graph_critical():
    # Critical anomaly (triggers breach simulation)
    graph = AttackGraphService.generate_attack_graph("Security Breach Vector", "CRITICAL")
    assert graph is not None
    assert "nodes" in graph
    assert "edges" in graph
    assert "summary" in graph

    # Verify nodes
    nodes = graph["nodes"]
    assert len(nodes) >= 4
    # User node check
    user_node = next((n for n in nodes if n["type"] == "user"), None)
    assert user_node is not None
    assert "access_level" in user_node["details"]

    # Verify edges MITRE mappings
    edges = graph["edges"]
    assert len(edges) >= 3
    assert any("T1566" in e["mitre_technique"] for e in edges)
    assert any("dwell_time_mins" in e for e in edges)

def test_generate_attack_graph_warning():
    # Warning anomaly (triggers normal performance simulation)
    graph = AttackGraphService.generate_attack_graph("CPU Anomaly Spike", "WARNING")
    assert graph is not None
    assert graph["summary"]["risk_index"] < 50

def test_attack_graph_endpoint(client, db_session):
    # Setup test incident
    from app.models.models import Incident
    from app.core.security import hash_password
    from app.models.models import User

    incident = Incident(
        correlation_id="attack-graph-test-1",
        source="Sentry",
        metric_type="UnauthorizedAccess",
        severity="CRITICAL",
        title="Unauthorized Database read",
        description="Database metrics threshold exceeded",
        status="INVESTIGATING",
        confidence_score=92
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    # Get credentials for engineer login
    user = db_session.query(User).filter(User.email == "engineer@sentinelflow.ai").first()
    if not user:
        user = User(
            email="engineer@sentinelflow.ai",
            hashed_password=hash_password("engineerpass"),
            full_name="SecOps Engineer",
            role="engineer",
            is_active=True
        )
        db_session.add(user)
    else:
        user.hashed_password = hash_password("engineerpass")
    db_session.commit()

    resp = client.post("/api/v1/auth/login", json={
        "email": "engineer@sentinelflow.ai",
        "password": "engineerpass"
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Query endpoint
    graph_resp = client.get(f"/api/v1/incidents/{incident.id}/attack-graph", headers=headers)
    assert graph_resp.status_code == 200
    res = graph_resp.json()
    assert "nodes" in res
    assert "edges" in res
    assert "summary" in res
