"""
SentinelFlow AI — API Endpoint Tests
Validates route authorizations, response schemas, and query inputs.
"""

import pytest
from app.core.security import create_access_token
from tests.factories.factories import create_user_factory, create_incident_factory


@pytest.fixture
def auth_headers(db_session):
    """Generate engineer access authentication headers."""
    user = create_user_factory(db_session, email="api_engineer@sentinelflow.ai", role="engineer")
    token = create_access_token({"sub": user.email, "role": user.role, "user_id": user.id})
    return {"Authorization": f"Bearer {token}"}


def test_api_list_incidents(client, auth_headers):
    """Verify HTTP GET incidents list returns collection format."""
    resp = client.get("/api/v1/incidents", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "incidents" in data
    assert isinstance(data["incidents"], list)


def test_api_get_incident_not_found(client, auth_headers):
    """Verify HTTP GET requesting non-existent IDs returns 404."""
    resp = client.get("/api/v1/incidents/999999", headers=auth_headers)
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_api_unauthorized_access(client):
    """Verify endpoint requests missing authorization fail with 401."""
    resp = client.get("/api/v1/incidents")
    assert resp.status_code == 401
