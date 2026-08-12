import pytest
from app.services.execution_mode_service import ExecutionModeService
from app.models.models import User, ExecutionConfig
from app.core.security import hash_password

@pytest.fixture
def auth_headers_user(client, db_session):
    user = db_session.query(User).filter(User.email == "op_user@sentinelflow.ai").first()
    if not user:
        user = User(
            email="op_user@sentinelflow.ai",
            hashed_password=hash_password("userpass123"),
            full_name="Ops User",
            role="engineer",
            is_active=True
        )
        db_session.add(user)
    else:
        user.hashed_password = hash_password("userpass123")
    db_session.commit()
    db_session.refresh(user)

    resp = client.post("/api/v1/auth/login", json={
        "email": "op_user@sentinelflow.ai",
        "password": "userpass123"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_default_operating_mode(db_session):
    """Test #1: Default operating mode exists and defaults safely."""
    cfg = ExecutionModeService.get_config(db_session)
    assert cfg.mode in ["MANUAL", "ASSISTED", "AUTONOMOUS"]

def test_authenticated_user_get_mode(client, auth_headers_user):
    """Test #2: Authenticated user can retrieve current operating mode."""
    resp = client.get("/api/v1/ops/execution-config", headers=auth_headers_user)
    assert resp.status_code == 200
    data = resp.json()
    assert "mode" in data
    assert "rate_limit_per_minute" in data

def test_authenticated_user_change_mode(client, auth_headers_user):
    """Test #3: Authenticated user can change operating mode."""
    payload = {
        "mode": "AUTONOMOUS",
        "rate_limit_per_minute": 8,
        "min_confidence_score": 92,
        "max_blast_radius": 6,
        "restricted_services": "payment,auth",
        "low_risk_actions": "restart_pod,scale_service"
    }
    resp = client.post("/api/v1/ops/execution-config", json=payload, headers=auth_headers_user)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "AUTONOMOUS"
    assert data["rate_limit_per_minute"] == 8

def test_invalid_mode_rejected(client, auth_headers_user):
    """Test #4: Invalid mode string is rejected with validation error."""
    payload = {
        "mode": "INVALID_RANDOM_MODE",
        "rate_limit_per_minute": 5,
        "min_confidence_score": 90,
        "max_blast_radius": 5,
        "restricted_services": "payment",
        "low_risk_actions": "restart_pod"
    }
    resp = client.post("/api/v1/ops/execution-config", json=payload, headers=auth_headers_user)
    assert resp.status_code == 422

def test_mode_persistence(client, db_session, auth_headers_user):
    """Test #5: Operating mode persists across requests and DB fetches."""
    payload = {
        "mode": "MANUAL",
        "rate_limit_per_minute": 12,
        "min_confidence_score": 95,
        "max_blast_radius": 4,
        "restricted_services": "database",
        "low_risk_actions": "restart_pod"
    }
    client.post("/api/v1/ops/execution-config", json=payload, headers=auth_headers_user)
    
    # Query again
    resp = client.get("/api/v1/ops/execution-config", headers=auth_headers_user)
    assert resp.status_code == 200
    assert resp.json()["mode"] == "MANUAL"
    assert resp.json()["rate_limit_per_minute"] == 12

    # Direct DB check
    cfg = ExecutionModeService.get_config(db_session)
    assert cfg.mode == "MANUAL"
    assert cfg.rate_limit_per_minute == 12

def test_manual_mode_requires_approval(db_session):
    """Test #6: MANUAL mode requires human approval."""
    ExecutionModeService.update_config(
        db=db_session,
        mode="MANUAL",
        rate_limit_per_minute=5,
        min_confidence_score=90,
        max_blast_radius=10,
        restricted_services="",
        low_risk_actions="restart_pod"
    )
    allowed, reason = ExecutionModeService.should_auto_execute(
        db=db_session,
        incident_id=1,
        confidence_score=99,
        action_command="restart_pod app",
        target_service="web-frontend",
        affected_services_count=1,
        severity="LOW"
    )
    assert allowed is False
    assert "MANUAL" in reason

def test_assisted_mode_requires_approval(db_session):
    """Test #7: ASSISTED mode requires human approval before execution."""
    ExecutionModeService.update_config(
        db=db_session,
        mode="ASSISTED",
        rate_limit_per_minute=5,
        min_confidence_score=90,
        max_blast_radius=10,
        restricted_services="",
        low_risk_actions="restart_pod"
    )
    allowed, reason = ExecutionModeService.should_auto_execute(
        db=db_session,
        incident_id=1,
        confidence_score=99,
        action_command="restart_pod app",
        target_service="web-frontend",
        affected_services_count=1,
        severity="LOW"
    )
    assert allowed is False
    assert "ASSISTED" in reason

def test_autonomous_mode_permits_execution(db_session):
    """Test #8: AUTONOMOUS mode permits execution when all safety gates pass."""
    ExecutionModeService.update_config(
        db=db_session,
        mode="AUTONOMOUS",
        rate_limit_per_minute=10,
        min_confidence_score=80,
        max_blast_radius=10,
        restricted_services="payment",
        low_risk_actions="restart_pod"
    )
    allowed, reason = ExecutionModeService.should_auto_execute(
        db=db_session,
        incident_id=1,
        confidence_score=95,
        action_command="restart_pod worker",
        target_service="worker-service",
        affected_services_count=1,
        severity="LOW"
    )
    assert allowed is True
    assert "AUTONOMOUS" in reason

def test_safety_validation_in_autonomous_mode(db_session):
    """Test #9: Safety validation still blocks unsafe actions in AUTONOMOUS mode."""
    ExecutionModeService.update_config(
        db=db_session,
        mode="AUTONOMOUS",
        rate_limit_per_minute=10,
        min_confidence_score=90,
        max_blast_radius=2,
        restricted_services="payment",
        low_risk_actions="restart_pod"
    )

    # 9a. Blast radius breach
    allowed, reason = ExecutionModeService.should_auto_execute(
        db=db_session,
        incident_id=1,
        confidence_score=95,
        action_command="restart_pod worker",
        target_service="worker-service",
        affected_services_count=5,  # Exceeds max_blast_radius=2
        severity="LOW"
    )
    assert allowed is False
    assert "blast radius" in reason.lower()

    # 9b. Restricted service
    allowed, reason = ExecutionModeService.should_auto_execute(
        db=db_session,
        incident_id=1,
        confidence_score=95,
        action_command="restart_pod payment-api",
        target_service="payment-api",
        affected_services_count=1,
        severity="LOW"
    )
    assert allowed is False
    assert "manual" in reason.lower()

def test_unauthenticated_user_cannot_modify(client):
    """Test #10: Unauthenticated request to update mode is rejected with 401."""
    payload = {
        "mode": "AUTONOMOUS",
        "rate_limit_per_minute": 5,
        "min_confidence_score": 90,
        "max_blast_radius": 5,
        "restricted_services": "payment",
        "low_risk_actions": "restart_pod"
    }
    resp = client.post("/api/v1/ops/execution-config", json=payload)
    assert resp.status_code == 401
