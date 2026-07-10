import pytest
from unittest.mock import AsyncMock, patch
from fastapi import status
from app.core.config import get_settings
from app.models.models import User
from app.core.security import hash_password

@pytest.fixture
def logged_in_engineer(client, db_session):
    """Fixture to register and login an engineer user for RBAC validation."""
    email = "test_eng_infra@sentinelflow.ai"
    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            hashed_password=hash_password("password123"),
            full_name="Infra Engineer",
            role="engineer",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    
    login_resp = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@patch("app.services.enkrypt_service.EnkryptAI")
def test_infra_execute_command_enkrypt_blocked(mock_enkrypt_class, client, db_session, logged_in_engineer):
    """Verify that a blocked command from Enkrypt AI returns a 403 Forbidden on the infra endpoint."""
    settings = get_settings()
    original_enabled = settings.ENKRYPTAI_ENABLED
    settings.ENKRYPTAI_ENABLED = True
    
    try:
        mock_client = mock_enkrypt_class.return_value
        
        from enkryptai import EnkryptAIResult
        mock_result = EnkryptAIResult(
            is_safe=False,
            risk_score=0.99,
            violations=["policy_violation"],
            message="Blocked by Enkrypt AI guardrails",
            redacted_content="rm -rf /"
        )
        
        mock_client.validate = AsyncMock(return_value=mock_result)
        
        response = client.post(
            "/api/v1/infra/execute-command",
            json={
                "command": "rm -rf /",
                "incident_id": 1
            },
            headers=logged_in_engineer
        )
        
        assert response.status_code == 403
        data = response.json()
        import json
        detail_data = json.loads(data["detail"])
        assert "Command blocked by Enkrypt AI guardrails" in detail_data["message"]
        assert detail_data["risk_score"] == 0.99
        assert "policy_violation" in detail_data["violations"]
        
    finally:
        settings.ENKRYPTAI_ENABLED = original_enabled


@patch("app.services.enkrypt_service.EnkryptAI")
def test_infra_execute_command_enkrypt_allowed(mock_enkrypt_class, client, db_session, logged_in_engineer):
    """Verify that an allowed command passes Enkrypt AI and executes successfully."""
    settings = get_settings()
    original_enabled = settings.ENKRYPTAI_ENABLED
    settings.ENKRYPTAI_ENABLED = True
    
    try:
        mock_client = mock_enkrypt_class.return_value
        
        from enkryptai import EnkryptAIResult
        mock_result = EnkryptAIResult(
            is_safe=True,
            risk_score=0.10,
            violations=[],
            message="Passed Enkrypt AI validation",
            redacted_content="kubectl get pods"
        )
        mock_client.validate = AsyncMock(return_value=mock_result)
        
        response = client.post(
            "/api/v1/infra/execute-command",
            json={
                "command": "kubectl get pods",
                "incident_id": 1
            },
            headers=logged_in_engineer
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ALLOWED"
        assert data["command"] == "kubectl get pods"
        assert data["risk_score"] == 0.10
        assert "LOW RISK" in data["risk_assessment"]
        
    finally:
        settings.ENKRYPTAI_ENABLED = original_enabled
