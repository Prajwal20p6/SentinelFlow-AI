import pytest
from app.models.models import User, Incident, IncidentComment
from app.core.security import hash_password

@pytest.fixture
def auth_headers(client, db_session):
    # Setup test user in the test database session
    user = db_session.query(User).filter(User.email == "test-engineer@sentinelflow.ai").first()
    if not user:
        user = User(
            email="test-engineer@sentinelflow.ai",
            hashed_password=hash_password("password123"),
            full_name="Test Engineer",
            role="engineer",
            is_active=True
        )
        db_session.add(user)
    else:
        user.hashed_password = hash_password("password123")
    db_session.commit()
    db_session.refresh(user)
    
    # Perform login via client
    resp = client.post("/api/v1/auth/login", json={
        "email": "test-engineer@sentinelflow.ai",
        "password": "password123"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_incident_comments_flow(client, db_session, auth_headers):
    # 1. Create a mock incident inside test database session
    incident = Incident(
        correlation_id="sf-test-incident-comments-123",
        source="Test Script",
        metric_type="CPU_SPIKE",
        severity="WARNING",
        title="Test Incident for Comments",
        description="Detailed test description",
        status="DETECTED"
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)
    inc_id = incident.id

    # 2. Add comment via API
    resp = client.post(
        f"/api/v1/incidents/{inc_id}/comments",
        json={"content": "This is a test comment from test suite"},
        headers=auth_headers
    )
    assert resp.status_code == 201
    assert resp.json()["author"] == "test-engineer@sentinelflow.ai"
    assert resp.json()["content"] == "This is a test comment from test suite"

    # 3. Retrieve comments via API
    resp = client.get(f"/api/v1/incidents/{inc_id}/comments", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
    assert resp.json()[0]["content"] == "This is a test comment from test suite"

def test_incident_analytics(client, db_session, auth_headers):
    resp = client.get("/api/v1/incidents/stats/analytics", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_count" in data
    assert "resolved_count" in data
    assert "resolution_rate" in data
    assert "mttr_seconds" in data
