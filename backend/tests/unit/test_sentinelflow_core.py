"""
SentinelFlow AI - Core Unit Test Suite.
Tests authentication, MFA setup/verification, RBAC authorization blocks, Enkrypt AI command validation,
and cryptographic audit trail ledger validations.
"""

import pytest
import pyotp
from fastapi import status
from app.models.models import User, AuditTrail
from app.services.safety_service import evaluate_command_safety, validate_audit_chain
from app.core.vector_db import get_text_embedding, init_qdrant_collections, search_similar_runbooks

# ── 1. Authentication & MFA Tests ──────────────────────────────
def test_user_registration_and_duplicate(client):
    """Test user registration and that duplicate emails are rejected."""
    # Register new user
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test_engineer@sentinelflow.ai",
            "password": "securepassword123",
            "full_name": "Test Engineer",
            "role": "engineer"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test_engineer@sentinelflow.ai"
    assert data["role"] == "engineer"
    assert data["mfa_enabled"] is False

    # Attempt to register duplicate email
    response_dup = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test_engineer@sentinelflow.ai",
            "password": "anotherpassword",
            "full_name": "Duplicate Test",
            "role": "viewer"
        }
    )
    assert response_dup.status_code == 409
    assert response_dup.json()["detail"] == "User with this email already exists"


def test_user_login_success_and_fail(client, db_session):
    """Test login authentication checks."""
    # Register user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "login_test@sentinelflow.ai",
            "password": "password123",
            "full_name": "Login Test",
            "role": "viewer"
        }
    )

    # Success login
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login_test@sentinelflow.ai", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "login_test@sentinelflow.ai"

    # Failed login (wrong password)
    response_fail = client.post(
        "/api/v1/auth/login",
        json={"email": "login_test@sentinelflow.ai", "password": "wrongpassword"}
    )
    assert response_fail.status_code == 401
    assert response_fail.json()["detail"] == "Invalid email or password"


def test_mfa_setup_enable_and_verify_flow(client):
    """Test full multi-factor authentication (MFA) setup, verify, and login challenge flow."""
    # 1. Register a user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "mfa_test@sentinelflow.ai",
            "password": "password123",
            "full_name": "MFA Test User",
            "role": "engineer"
        }
    )

    # 2. Login to get token
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "mfa_test@sentinelflow.ai", "password": "password123"}
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Call MFA Setup
    setup_resp = client.post("/api/v1/auth/mfa/setup", headers=headers)
    assert setup_resp.status_code == 200
    setup_data = setup_resp.json()
    assert "secret" in setup_data
    assert "qr_uri" in setup_data
    secret = setup_data["secret"]

    # 4. Generate valid TOTP token and enable MFA
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()

    enable_resp = client.post(
        "/api/v1/auth/mfa/enable",
        json={"code": valid_code},
        headers=headers
    )
    assert enable_resp.status_code == 200
    assert enable_resp.json()["mfa_enabled"] is True

    # 5. Verify that login now triggers an MFA challenge
    login_challenge_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "mfa_test@sentinelflow.ai", "password": "password123"}
    )
    # The endpoint returns a prompt/challenge response without token if MFA is enabled but header is missing
    # In router_auth.py:
    # return { "message": "MFA verification required...", "mfa_required": True } OR similar model
    challenge_data = login_challenge_resp.json()
    assert challenge_data.get("access_token") is None

    # 6. Login with valid MFA token header
    valid_code_new = totp.now()
    login_success_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "mfa_test@sentinelflow.ai", "password": "password123"},
        headers={"X-MFA-Token": valid_code_new}
    )
    assert login_success_resp.status_code == 200
    assert "access_token" in login_success_resp.json()

    # 7. Disable MFA
    disable_resp = client.post("/api/v1/auth/mfa/disable", headers=headers)
    assert disable_resp.status_code == 200
    assert disable_resp.json()["mfa_enabled"] is False


# ── 2. RBAC Authorization & Role Block Tests ─────────────────────
def test_rbac_access_restrictions(client):
    """Test RBAC role-level boundary checks for Viewer, Engineer, and Admin roles."""
    # Register Viewer, Engineer, and Admin users
    import random
    suffix = str(random.randint(1000, 9999))
    email_view = f"view_{suffix}@sentinelflow.ai"
    email_eng = f"eng_{suffix}@sentinelflow.ai"
    email_adm = f"adm_{suffix}@sentinelflow.ai"

    client.post("/api/v1/auth/register", json={"email": email_view, "password": "password123", "role": "viewer"})
    client.post("/api/v1/auth/register", json={"email": email_eng, "password": "password123", "role": "engineer"})
    client.post("/api/v1/auth/register", json={"email": email_adm, "password": "password123", "role": "admin"})

    # Get login tokens
    view_token = client.post("/api/v1/auth/login", json={"email": email_view, "password": "password123"}).json()["access_token"]
    eng_token = client.post("/api/v1/auth/login", json={"email": email_eng, "password": "password123"}).json()["access_token"]
    adm_token = client.post("/api/v1/auth/login", json={"email": email_adm, "password": "password123"}).json()["access_token"]

    # Endpoints to test:
    # 1. /api/v1/infra/topology (Viewer-level)
    # 2. /api/v1/infra/execute-command (Engineer-level)
    # 3. /api/v1/infra/audit-trail/verify (Admin-level)

    # Test Viewer Access
    view_headers = {"Authorization": f"Bearer {view_token}"}
    assert client.get("/api/v1/infra/topology", headers=view_headers).status_code == 200
    assert client.post("/api/v1/infra/execute-command", json={"command": "kubectl get pods"}, headers=view_headers).status_code == 403
    assert client.get("/api/v1/infra/audit-trail/verify", headers=view_headers).status_code == 403

    # Test Engineer Access
    eng_headers = {"Authorization": f"Bearer {eng_token}"}
    assert client.get("/api/v1/infra/topology", headers=eng_headers).status_code == 200
    assert client.post("/api/v1/infra/execute-command", json={"command": "kubectl get pods"}, headers=eng_headers).status_code == 200
    assert client.get("/api/v1/infra/audit-trail/verify", headers=eng_headers).status_code == 403

    # Test Admin Access
    adm_headers = {"Authorization": f"Bearer {adm_token}"}
    assert client.get("/api/v1/infra/topology", headers=adm_headers).status_code == 200
    assert client.post("/api/v1/infra/execute-command", json={"command": "kubectl get pods"}, headers=adm_headers).status_code == 200
    assert client.get("/api/v1/infra/audit-trail/verify", headers=adm_headers).status_code == 200


# ── 3. Enkrypt AI & Cryptographic Audit Ledger Tests ───────────────
def test_enkrypt_command_safety_checks():
    """Verify Enkrypt AI safety guard blocks critical commands while clearing safe commands."""
    # Critical Commands (Risk 0.99) -> Should block
    status, risk, desc = evaluate_command_safety("rm -rf /")
    assert status == "BLOCKED"
    assert risk == 0.99
    assert "CRITICAL RISK" in desc

    status, risk, desc = evaluate_command_safety("dd if=/dev/zero of=/dev/sda")
    assert status == "BLOCKED"
    assert risk == 0.99

    # High Risk Commands (Risk 0.85) -> Should block
    status, risk, desc = evaluate_command_safety("kubectl delete namespace kube-system")
    assert status == "BLOCKED"
    assert risk == 0.85
    assert "HIGH RISK" in desc

    # Moderate Risk (Risk 0.50) -> Allowed
    status, risk, desc = evaluate_command_safety("kubectl scale deployment/my-app --replicas=0")
    assert status == "ALLOWED"
    assert risk == 0.50

    # Low Risk (Risk 0.10) -> Allowed
    status, risk, desc = evaluate_command_safety("kubectl rollout restart deployment/my-app")
    assert status == "ALLOWED"
    assert risk == 0.10


def test_audit_trail_cryptographic_ledger(db_session):
    """Test cryptographic chaining of audit logs and verification of ledger validation."""
    from app.services.safety_service import execute_guarded_command

    # Clear previous audit trails in db
    db_session.query(AuditTrail).delete()
    db_session.commit()

    # Log several commands to construct audit chain
    execute_guarded_command(db_session, "kubectl get pods", performed_by="user1")
    execute_guarded_command(db_session, "kubectl rollout restart deployment/app", performed_by="user2")
    execute_guarded_command(db_session, "rm -rf /etc/kubernetes/manifests", performed_by="user1")

    # Validate ledger is initially intact
    status_intact = validate_audit_chain(db_session)
    assert status_intact["valid"] is True
    assert status_intact["count"] == 3

    # Tamper with block audit entry 2
    second_audit = db_session.query(AuditTrail).filter(AuditTrail.id == 2).first()
    second_audit.command_checked = "kubectl delete namespace default"  # Modifying command content
    db_session.commit()

    # Validate chain is now broken
    status_broken = validate_audit_chain(db_session)
    assert status_broken["valid"] is False
    assert "Chain broken" in status_broken["message"]


# ── 4. Qdrant / Vector DB RAG Retrieval Tests ───────────────────────
def test_qdrant_embeddings_and_retrieval():
    """Verify deterministic pseudo-embedding generation and RAG runbook search."""
    # Verify pseudo-embedding returns expected dimensions
    embedding = get_text_embedding("kubectl CPU exhaustion spike on node-01")
    assert isinstance(embedding, list)
    assert len(embedding) == 384
    # Normalization check
    import numpy as np
    norm = np.linalg.norm(embedding)
    assert abs(norm - 1.0) < 1e-4

    # Seed runbooks collection
    init_qdrant_collections()

    # Search runbooks
    results = search_similar_runbooks("High memory exhaustion OOM warning", limit=2)
    assert len(results) >= 1
    # Check that it returns formatted matches
    assert "title" in results[0]
    assert "content" in results[0]
    assert "score" in results[0]
