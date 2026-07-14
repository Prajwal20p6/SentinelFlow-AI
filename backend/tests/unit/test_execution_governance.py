import pytest
from app.services.execution_mode_service import ExecutionModeService
from app.models.models import User
from app.core.security import hash_password

@pytest.fixture
def auth_headers_admin(client, db_session):
    user = db_session.query(User).filter(User.email == "admin@sentinelflow.ai").first()
    if not user:
        user = User(
            email="admin@sentinelflow.ai",
            hashed_password=hash_password("adminpass"),
            full_name="Administrator",
            role="admin",
            is_active=True
        )
        db_session.add(user)
    else:
        user.hashed_password = hash_password("adminpass")
    db_session.commit()
    db_session.refresh(user)

    resp = client.post("/api/v1/auth/login", json={
        "email": "admin@sentinelflow.ai",
        "password": "adminpass"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_governance_rules_eval(db_session):
    # Set to MANUAL
    cfg = ExecutionModeService.update_config(
        db=db_session,
        mode="MANUAL",
        rate_limit_per_minute=5,
        min_confidence_score=90,
        max_blast_radius=5,
        restricted_services="billing",
        low_risk_actions="restart_pod,scale_service,restart_deployment,rollout_restart"
    )
    
    # MANUAL triggers block
    allowed, reason = ExecutionModeService.should_auto_execute(
        db=db_session,
        incident_id=1,
        confidence_score=95,
        action_command="restart_pod",
        target_service="catalog",
        affected_services_count=1,
        severity="CRITICAL"
    )
    assert allowed is False
    assert "MANUAL" in reason

    # SEMI_AUTONOMOUS configuration
    ExecutionModeService.update_config(
        db=db_session,
        mode="SEMI_AUTONOMOUS",
        rate_limit_per_minute=5,
        min_confidence_score=90,
        max_blast_radius=5,
        restricted_services="billing",
        low_risk_actions="restart_pod,scale_service,restart_deployment,rollout_restart"
    )

    # 1. Test P0 (CRITICAL) - allowed actions (Restart pod, scale service, restart deployment)
    # Confidence >= 85
    allowed, reason = ExecutionModeService.should_auto_execute(
        db=db_session,
        incident_id=1,
        confidence_score=87,
        action_command="restart_pod catalog-deployment",
        target_service="catalog",
        affected_services_count=1,
        severity="CRITICAL"
    )
    assert allowed is True

    # Confidence < 85
    allowed, reason = ExecutionModeService.should_auto_execute(
        db=db_session,
        incident_id=1,
        confidence_score=82,
        action_command="restart_pod catalog-deployment",
        target_service="catalog",
        affected_services_count=1,
        severity="CRITICAL"
    )
    assert allowed is False
    assert "below P0 threshold" in reason

    # 2. Test P1 (HIGH) - allowed actions (Restart pod, scale service)
    # Confidence >= 90
    allowed, reason = ExecutionModeService.should_auto_execute(
        db=db_session,
        incident_id=1,
        confidence_score=92,
        action_command="scale_service catalog-replica",
        target_service="catalog",
        affected_services_count=1,
        severity="HIGH"
    )
    assert allowed is True

    # Exclude deployment actions for P1
    allowed, reason = ExecutionModeService.should_auto_execute(
        db=db_session,
        incident_id=1,
        confidence_score=95,
        action_command="restart_deployment catalog",
        target_service="catalog",
        affected_services_count=1,
        severity="HIGH"
    )
    assert allowed is False
    assert "Deployment actions are not allowed for P1" in reason

    # Confidence < 90
    allowed, reason = ExecutionModeService.should_auto_execute(
        db=db_session,
        incident_id=1,
        confidence_score=88,
        action_command="restart_pod catalog",
        target_service="catalog",
        affected_services_count=1,
        severity="HIGH"
    )
    assert allowed is False
    assert "below P1 threshold" in reason

    # 3. Test P2 (MEDIUM) & P3 (LOW) - requires manual approval
    allowed, reason = ExecutionModeService.should_auto_execute(
        db=db_session,
        incident_id=1,
        confidence_score=95,
        action_command="restart_pod catalog",
        target_service="catalog",
        affected_services_count=1,
        severity="MEDIUM"
    )
    assert allowed is False
    assert "Manual approval required" in reason

    # 4. Per-Service Overrides
    # Payment API override
    allowed, reason = ExecutionModeService.should_auto_execute(
        db=db_session,
        incident_id=1,
        confidence_score=95,
        action_command="restart_pod",
        target_service="payment-api",
        affected_services_count=1,
        severity="CRITICAL"
    )
    assert allowed is False
    assert "Payment API always requires manual approval" in reason

    # Database override
    allowed, reason = ExecutionModeService.should_auto_execute(
        db=db_session,
        incident_id=1,
        confidence_score=95,
        action_command="restart_pod",
        target_service="postgres-db",
        affected_services_count=1,
        severity="CRITICAL"
    )
    assert allowed is False
    assert "Database always requires manual approval" in reason

    # Cache service override (can auto execute low-risk)
    allowed, reason = ExecutionModeService.should_auto_execute(
        db=db_session,
        incident_id=1,
        confidence_score=95,
        action_command="restart_pod",
        target_service="redis-cache",
        affected_services_count=1,
        severity="CRITICAL"
    )
    assert allowed is True

def test_execution_config_endpoint(client, db_session, auth_headers_admin):
    # Fetch
    resp = client.get("/api/v1/execution-config")
    assert resp.status_code == 200
    assert resp.json()["mode"] in ["MANUAL", "SEMI_AUTONOMOUS", "FULLY_AUTONOMOUS"]

    # Update
    update_payload = {
        "mode": "FULLY_AUTONOMOUS",
        "rate_limit_per_minute": 10,
        "min_confidence_score": 95,
        "max_blast_radius": 8,
        "restricted_services": "payment,checkout",
        "low_risk_actions": "restart_pod"
    }
    post_resp = client.post("/api/v1/execution-config", json=update_payload, headers=auth_headers_admin)
    assert post_resp.status_code == 200
    assert post_resp.json()["mode"] == "FULLY_AUTONOMOUS"
    assert post_resp.json()["min_confidence_score"] == 95
