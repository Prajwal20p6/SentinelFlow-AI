"""
SentinelFlow AI — Production Authentication Security Unit Tests
"""

import pytest
from app.services.auth_service import generate_verification_token, generate_reset_token


def test_register_response_does_not_expose_verification_token(client):
    """Verify register endpoint response never contains raw verification_token."""
    payload = {
        "email": "authtest_register@sentinelflow.ai",
        "password": "Password123!",
        "full_name": "Auth Test User",
        "role": "engineer"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code in (201, 409)
    if response.status_code == 201:
        data = response.json()
        assert "verification_token" not in data
        assert "password" not in data
        assert "message" in data


def test_forgot_password_response_does_not_expose_reset_token(client):
    """Verify forgot-password endpoint response never contains raw reset_token."""
    payload = {"email": "admin@sentinelflow.ai"}
    response = client.post("/api/v1/auth/forgot-password", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "reset_token" not in data
    assert "password_reset_token" not in data
    assert "message" in data


def test_resend_verification_endpoint(client):
    """Verify resend-verification endpoint handles requests safely."""
    payload = {"email": "admin@sentinelflow.ai"}
    response = client.post("/api/v1/auth/resend-verification", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "verification_token" not in data
    assert "email" in data


def test_google_auth_invalid_token_returns_401(client):
    """Verify /auth/google rejects invalid/fake tokens with HTTP 401."""
    payload = {"credential": "invalid_fake_google_token_12345"}
    response = client.post("/api/v1/auth/google", json=payload)
    assert response.status_code == 401
    assert "Invalid" in response.json()["detail"] or "expired" in response.json()["detail"]


def test_verify_email_roundtrip(client):
    """Verify email token verification works end-to-end."""
    email = "admin@sentinelflow.ai"
    token = generate_verification_token(email)
    response = client.post(f"/api/v1/auth/verify-email?token={token}")
    assert response.status_code == 200
    assert response.json()["verified"] is True
