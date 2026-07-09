# SentinelFlow AI — Production REST API Documentation

This guide describes the core API endpoints of the SentinelFlow AI SecOps engine.

---

## 1. Authentication (`/api/v1/auth`)

All requests (excluding login, registration, and telemetry ingest) require JWT token headers:
`Authorization: Bearer <token>`

### Register User
* **Method & Route**: `POST /api/v1/auth/register`
* **Request Body**:
```json
{
  "email": "user@example.com",
  "password": "strong-password-here",
  "full_name": "John Doe",
  "role": "engineer"
}
```
* **Response (201 Created)**:
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "engineer",
  "is_active": true,
  "mfa_enabled": false
}
```

### Log In (OAuth2 Token Request)
* **Method & Route**: `POST /api/v1/auth/login`
* **Request Header (Optional for MFA)**: `X-MFA-Token: <6-digit-totp>`
* **Request Form Data**:
  - `username`: Email address
  - `password`: Password
* **Response (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6Ikp...",
  "token_type": "bearer"
}
```

### Multi-Factor Authentication Configuration
* **Get Setup Secret**: `POST /api/v1/auth/mfa/setup` -> Returns standard base32 MFA secret and QR code URI.
* **Enable MFA**: `POST /api/v1/auth/mfa/enable` with body `{"token": "123456"}` -> Activates MFA checks.

---

## 2. Telemetry Ingestion (`/api/v1/telemetry`)

Open endpoint (no auth required) designed for container metric pipelines.

### Ingest Metrics
* **Method & Route**: `POST /api/v1/telemetry/ingest`
* **Query Parameter**: `format` (Options: `json`, `prometheus`, `kubernetes_event`)
* **Payload Examples**:
  - **json**:
  ```json
  {
    "node_name": "worker-node-03",
    "namespace": "default",
    "disk_usage": 95.8
  }
  ```
* **Response (202 Accepted)**:
```json
{
  "status": "ok",
  "correlation_id": "sf-trace-574d0ae6ab72",
  "anomalies_detected": ["DISK_FULL"]
}
```

---

## 3. Incident Management (`/api/v1/incidents`)

### List Incidents
* **Method & Route**: `GET /api/v1/incidents`
* **Query Parameters**: `page` (default 1), `size` (default 20), `status` (optional filter)
* **Response (200 OK)**:
```json
{
  "incidents": [
    {
      "id": 1,
      "source": "K8s Telemetry Monitor",
      "metric_type": "DISK_FULL",
      "severity": "CRITICAL",
      "status": "RESOLVED",
      "title": "Disk Full on worker-node-03"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 20
}
```

### Get Detailed Forensics & Timelines
* **Get Timeline**: `GET /api/v1/incidents/{incident_id}/timeline` -> Returns all Mastra state transition events.
* **Get Explainability Report**: `GET /api/v1/incidents/{incident_id}/forensics` -> Returns Markdown explanation of LLM/safety actions.
