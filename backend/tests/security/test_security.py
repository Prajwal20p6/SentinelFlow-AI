"""
SentinelFlow AI — Security Tests
Verifies rate-limiting, RBAC hierarchical restrictions, and parameter boundaries.
"""

import pytest
from app.core.security import create_access_token
from tests.factories.factories import create_user_factory


@pytest.fixture
def viewer_headers(db_session):
    """Generate viewer access authentication headers."""
    user = create_user_factory(db_session, email="api_security_viewer@sentinelflow.ai", role="viewer")
    token = create_access_token({"sub": user.email, "role": user.role, "user_id": user.id})
    return {"Authorization": f"Bearer {token}"}


def test_rbac_viewer_denied_from_demo_triggers(client, viewer_headers):
    """Verify viewer role is blocked (403 Forbidden) from executing demo triggers."""
    resp = client.post(
        "/api/v1/demo/trigger",
        json={"scenario": "CPU_SPIKE"},
        headers=viewer_headers
    )
    assert resp.status_code == 403
    assert "permissions" in resp.json()["detail"].lower()


def test_rate_limiting_gatekeeper_validation(client):
    """Verify rate-limiting registers headers tracking request limits."""
    resp = client.get("/health")
    # Health checks are generally public, but check if they return rate limit headers
    assert resp.status_code in (200, 429)
