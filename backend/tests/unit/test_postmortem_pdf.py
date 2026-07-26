import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.models import Incident, User
from app.core.security import hash_password, create_access_token

@pytest.fixture
def auth_headers(db_session):
    """Fixture providing an authenticated engineer header."""
    user = User(
        email="pdf_tester@sentinelflow.ai",
        hashed_password=hash_password("PdfPass123!"),
        role="engineer"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token({"sub": user.email, "role": user.role})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def sample_incident(db_session):
    """Fixture providing a sample resolved incident for PDF testing."""
    inc = Incident(
        correlation_id="sf-pdf-test-1001",
        source="k8s-exporter",
        metric_type="CPU_SPIKE",
        severity="CRITICAL",
        title="CPU Spike on node-01/redis-cache",
        description="CPU utilization exceeded 95% threshold for 10 consecutive minutes",
        status="EXECUTED",
        suggested_action="Scale deployment replicas from 2 to 5"
    )
    db_session.add(inc)
    db_session.commit()
    db_session.refresh(inc)
    return inc

def test_export_postmortem_pdf_endpoint(db_session, auth_headers, sample_incident):
    """Test PDF export endpoint returning real PDF binary document starting with %PDF- header."""
    client = TestClient(app)
    response = client.get(
        f"/api/v1/incidents/{sample_incident.id}/postmortem/pdf",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert f"postmortem_incident_{sample_incident.id}.pdf" in response.headers["content-disposition"]
    
    # Critical assertion: Verify response bytes start with real %PDF- magic header
    pdf_bytes = response.content
    assert pdf_bytes.startswith(b"%PDF-"), f"Response bytes did not start with %PDF- header! Received: {pdf_bytes[:20]}"
    assert len(pdf_bytes) > 1000, f"Generated PDF file size is unexpectedly small: {len(pdf_bytes)} bytes"
