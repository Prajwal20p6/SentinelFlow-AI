"""
SentinelFlow AI — End-to-End (E2E) Scenario Tests
Simulates real-world workflows from telemetry anomalies to incident resolution.
"""

import pytest
from app.core.security import create_access_token
from tests.factories.factories import create_user_factory


@pytest.fixture
def admin_headers(db_session):
    """Generate admin access authentication headers."""
    user = create_user_factory(db_session, email="e2e_admin@sentinelflow.ai", role="admin")
    token = create_access_token({"sub": user.email, "role": user.role, "user_id": user.id})
    return {"Authorization": f"Bearer {token}"}


def test_e2e_incident_self_healing_flow(client, admin_headers):
    """E2E flow: Ingest storage anomaly -> verify incident created."""
    # 1. Ingest telemetry disk warning
    resp_ingest = client.post(
        "/api/v1/telemetry/ingest",
        json={
            "node_name": "worker-node-03",
            "namespace": "default",
            "disk_usage": 95.8
        }
    )
    assert resp_ingest.status_code == 202

    # 2. Check incident registry feed for generated ticket
    resp_list = client.get("/api/v1/incidents", headers=admin_headers)
    assert resp_list.status_code == 200
    incidents = resp_list.json()["incidents"]
    assert len(incidents) > 0

    # Match latest incident source
    latest = incidents[0]
    assert latest["source"] == "K8s Telemetry Monitor"
