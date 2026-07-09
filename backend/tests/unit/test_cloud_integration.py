import pytest
from app.services.cloud_service import remediation_manager, KubernetesClient, AWSClient, GCPClient
from app.models.models import Incident, RemediationExecution, User
from app.core.security import hash_password

@pytest.fixture
def admin_headers(client, db_session):
    user = db_session.query(User).filter(User.email == "admin-cloud@sentinelflow.ai").first()
    if not user:
        user = User(
            email="admin-cloud@sentinelflow.ai",
            hashed_password=hash_password("adminpass"),
            full_name="Admin User",
            role="admin",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
    resp = client.post("/api/v1/auth/login", json={
        "email": "admin-cloud@sentinelflow.ai",
        "password": "adminpass"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_cloud_clients_simulation():
    k8s = KubernetesClient()
    assert "[DRY-RUN]" in k8s.restart_pod("default", "web-pod", dry_run=True)
    assert "Executed pod restart" in k8s.restart_pod("default", "web-pod", dry_run=False)

    aws = AWSClient()
    assert "[DRY-RUN]" in aws.restart_ec2_instance("i-12345", "us-east-1", dry_run=True)
    assert "Rebooted successfully" in aws.restart_ec2_instance("i-12345", "us-east-1", dry_run=False)

    gcp = GCPClient()
    assert "[DRY-RUN]" in gcp.restart_compute_instance("gcp-node", "us-east1-b", "proj-1", dry_run=True)

def test_remediation_execution_and_rollback(db_session):
    incident = Incident(
        title="Scaling Incident",
        source="k8s",
        metric_type="CPU_SPIKE",
        severity="medium",
        status="DETECTED",
        description="CPU Spike details",
        correlation_id="cloud-test-cid-900"
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    # 1. Execute action
    cmd = "kubectl scale deployment/api-gateway --replicas=3 -n default"
    res = remediation_manager.execute_action(db_session, incident.id, cmd, performed_by="test-agent")
    assert res["status"] == "SUCCESS"
    
    exec_id = res["execution_id"]
    row = db_session.query(RemediationExecution).filter(RemediationExecution.id == exec_id).first()
    assert row is not None
    assert row.command == cmd

    # 2. Rollback action
    roll = remediation_manager.rollback_execution(db_session, exec_id, performed_by="admin-user")
    assert roll["rollback_status"] == "SUCCESS"
    assert "replicas=1" in roll["rollback_command"]

def test_rollback_api_endpoint(client, db_session, admin_headers):
    # 1. Create a mock execution
    incident = Incident(
        title="Mock Rollback Incident",
        source="k8s",
        metric_type="CPU_SPIKE",
        severity="medium",
        status="DETECTED",
        description="CPU Spike details",
        correlation_id="cloud-api-cid-900"
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    exec_record = RemediationExecution(
        incident_id=incident.id,
        command="kubectl scale deployment/api-gateway --replicas=3 -n default",
        execution_status="SUCCESS",
        console_output="Scaled successfully",
        executed_by="workflow"
    )
    db_session.add(exec_record)
    db_session.commit()
    db_session.refresh(exec_record)

    # 2. Trigger rollback endpoint
    resp = client.post(f"/api/v1/infra/remediations/{exec_record.id}/rollback", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["rollback_status"] == "SUCCESS"
    assert resp.json()["original_execution_id"] == exec_record.id
