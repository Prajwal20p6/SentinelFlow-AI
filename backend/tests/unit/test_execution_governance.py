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

    # AUTONOMOUS configuration
    ExecutionModeService.update_config(
        db=db_session,
        mode="AUTONOMOUS",
        rate_limit_per_minute=5,
        min_confidence_score=85,
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
    assert "configured threshold" in reason.lower()

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

    # High risk action denied
    allowed, reason = ExecutionModeService.should_auto_execute(
        db=db_session,
        incident_id=1,
        confidence_score=95,
        action_command="delete pod catalog",
        target_service="catalog",
        affected_services_count=1,
        severity="HIGH"
    )
    assert allowed is False
    assert "high-risk" in reason.lower()

    # Confidence < min_confidence_score (85)
    allowed, reason = ExecutionModeService.should_auto_execute(
        db=db_session,
        incident_id=1,
        confidence_score=80,
        action_command="restart_pod catalog",
        target_service="catalog",
        affected_services_count=1,
        severity="HIGH"
    )
    assert allowed is False
    assert "configured threshold" in reason.lower()

    # 3. Test ASSISTED mode - requires manual approval
    ExecutionModeService.update_config(
        db=db_session,
        mode="ASSISTED",
        rate_limit_per_minute=5,
        min_confidence_score=90,
        max_blast_radius=5,
        restricted_services="billing",
        low_risk_actions="restart_pod"
    )
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
    assert "ASSISTED" in reason

    # Restore AUTONOMOUS for per-service overrides
    ExecutionModeService.update_config(
        db=db_session,
        mode="AUTONOMOUS",
        rate_limit_per_minute=5,
        min_confidence_score=85,
        max_blast_radius=5,
        restricted_services="billing",
        low_risk_actions="restart_pod"
    )

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
    from app.main import app
    from app.api.router_ops import router as ops_router
    if not any(hasattr(r, "path") and "/execution-config" in r.path for r in app.routes):
        app.include_router(ops_router, prefix="/api/v1")

    # Fetch
    resp = client.get("/api/v1/execution-config", headers=auth_headers_admin)
    assert resp.status_code == 200
    assert resp.json()["mode"] in ["MANUAL", "ASSISTED", "AUTONOMOUS"]

    # Update
    update_payload = {
        "mode": "AUTONOMOUS",
        "rate_limit_per_minute": 10,
        "min_confidence_score": 95,
        "max_blast_radius": 8,
        "restricted_services": "payment,checkout",
        "low_risk_actions": "restart_pod"
    }
    post_resp = client.post("/api/v1/execution-config", json=update_payload, headers=auth_headers_admin)
    assert post_resp.status_code == 200
    assert post_resp.json()["mode"] == "AUTONOMOUS"
    assert post_resp.json()["min_confidence_score"] == 95
