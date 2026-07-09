# SentinelFlow AI — API Reference Manual

This document details the standard REST API routes exposed by the SentinelFlow AI backend on port `8000`.

## 1. Authentication Router (`/api/v1/auth`)

### Register User
- **Method**: `POST`
- **Path**: `/register`
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "secure_password_123",
    "full_name": "John Doe",
    "role": "engineer"
  }
  ```
- **Response**: `201 Created`
  ```json
  {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "engineer",
    "is_active": true,
    "mfa_enabled": false,
    "created_at": "2026-07-06T12:00:00Z"
  }
  ```

### User Login (MFA Aware)
- **Method**: `POST`
- **Path**: `/login`
- **Headers**:
  - `X-MFA-Token` (Optional): 6-digit TOTP verification token.
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "secure_password_123"
  }
  ```
- **Response (MFA Disabled or Code Provided)**: `200 OK`
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user": {
      "id": 1,
      "email": "user@example.com",
      "full_name": "John Doe",
      "role": "engineer",
      "is_active": true,
      "mfa_enabled": false,
      "created_at": "2026-07-06T12:00:00Z"
    }
  }
  ```
- **Response (MFA Enabled but Code Missing)**: `200 OK` (MFA Challenge)
  ```json
  {
    "detail": "MFA_REQUIRED",
    "mfa_required": true
  }
  ```

---

## 2. Infrastructure & Safety Router (`/api/v1/infra`)

### Execute Guarded Command
- **Method**: `POST`
- **Path**: `/execute-command`
- **Authentication**: JWT token required (`engineer` or `admin` role).
- **Request Body**:
  ```json
  {
    "command": "kubectl rollout restart deployment/payment-gateway",
    "incident_id": 4
  }
  ```
- **Response (Allowed)**: `200 OK`
  ```json
  {
    "command": "kubectl rollout restart deployment/payment-gateway",
    "status": "ALLOWED",
    "risk_score": 0.10,
    "risk_assessment": "LOW RISK: Command matches known safe patterns.",
    "execution_output": "deployment.apps/payment-gateway restarted successfully",
    "audit_id": 42
  }
  ```
- **Response (Blocked)**: `200 OK`
  ```json
  {
    "command": "rm -rf /etc/kubernetes/manifests",
    "status": "BLOCKED",
    "risk_score": 0.99,
    "risk_assessment": "CRITICAL RISK: File deletion traversal command.",
    "execution_output": null,
    "audit_id": 43
  }
  ```

### Verify Audit Ledger Hash Chain
- **Method**: `GET`
- **Path**: `/audit-trail/verify`
- **Authentication**: JWT token required (`admin` role only).
- **Response**: `200 OK`
  ```json
  {
    "valid": true,
    "message": "Blockchain ledger integrity verified successfully.",
    "count": 43
  }
  ```

---

## 3. Incident Router (`/api/v1/incidents`)

### List Incidents
- **Method**: `GET`
- **Path**: `/?status=PENDING_APPROVAL&severity=CRITICAL&page=1&per_page=20`
- **Authentication**: JWT token required.
- **Response**: `200 OK`
  ```json
  {
    "incidents": [
      {
        "id": 4,
        "correlation_id": "sf-trace-d397fb71",
        "source": "K8s Telemetry Monitor",
        "metric_type": "CPU_SPIKE",
        "severity": "CRITICAL",
        "title": "CPU Exhaustion on node-01",
        "description": "High CPU consumption alert triggered",
        "status": "PENDING_APPROVAL",
        "confidence_score": 0.85,
        "suggested_action": "kubectl scale deployment/payment-gateway --replicas=3",
        "assigned_to": null,
        "resolved_at": null,
        "created_at": "2026-07-06T12:30:00Z",
        "updated_at": "2026-07-06T12:30:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "per_page": 20
  }
  ```

### Approve Incident Remediation (HITL)
- **Method**: `POST`
- **Path**: `/{incident_id}/approve`
- **Authentication**: JWT token required (`engineer` or `admin` role).
- **Response**: `200 OK`
  ```json
  {
    "message": "Incident approved and executed.",
    "incident": {
      "id": 4,
      "correlation_id": "sf-trace-d397fb71",
      "status": "EXECUTED",
      "confidence_score": 0.85,
      "suggested_action": "kubectl scale deployment/payment-gateway --replicas=3",
      "assigned_to": "engineer@sentinelflow.ai",
      "resolved_at": "2026-07-06T12:31:05Z",
      "created_at": "2026-07-06T12:30:00Z",
      "updated_at": "2026-07-06T12:31:05Z"
    }
  }
  ```
