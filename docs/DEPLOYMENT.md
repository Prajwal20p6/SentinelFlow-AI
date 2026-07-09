# SentinelFlow AI — Production Deployment Guide

This guide details the step-by-step installation instructions to deploy SentinelFlow AI into production container runtimes.

---

## 1. Prerequisites

- **Docker Compose**: Version 2.0+
- **Kubernetes Cluster**: Kubernetes 1.25+ with `kubectl` configured.
- **Hardware Profile**: 
  - Backend: 1 Core CPU, 1GB RAM minimum.
  - Frontend: 1 Core CPU, 512MB RAM minimum.

---

## 2. Environment Configurations

Create a production `.env` configuration file mapping settings:

```ini
# General Settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Backend CORS Specific Origins (Change to your domain)
ALLOWED_ORIGINS=https://sentinelflow.company.com,https://api.sentinelflow.company.com

# Production PostgreSQL Database URL
DATABASE_URL=postgresql+asyncpg://sentinelflow:secure-password@postgres-host:5432/sentinelflow

# Redis URL for WebSocket connection scalability and caches
REDIS_URL=redis://redis-host:6379/0

# Qdrant Vector DB Settings
QDRANT_MODE=server
QDRANT_HOST=qdrant-host
QDRANT_PORT=6333

# Secure Crypto Keys (Must be randomized strings)
SECRET_KEY=highly-secured-randomized-jwt-secret-string-here
ENCRYPTION_KEY=secure-aes-encryption-key-must-be-32-chars-long!
```

---

## 3. Docker Compose Orchestration

To run the full stack locally with compose:

1. Clone the project repository.
2. Configure `.env` using `.env.example` configurations.
3. Launch services:
   ```bash
   docker compose -f docker/docker-compose.yml up --build -d
   ```
4. Access the React dashboard at `http://localhost:3000` and FastAPI OpenAPI docs at `http://localhost:8000/docs`.

---

## 4. Kubernetes Deployment Steps

Deploy resources using the files located in the `kubernetes/` folder:

1. **Config Map & Secrets**:
   Create base64 secrets mapping your database credentials, encryption key, and JWT secret:
   ```bash
   kubectl apply -f kubernetes/configmap.yaml
   kubectl apply -f kubernetes/secrets.yaml
   ```
2. **Deploy Pods and Services**:
   Apply deployment specifications mapping Kubernetes pods scaling constraints and load balancing service routes:
   ```bash
   kubectl apply -f kubernetes/deployment.yaml
   kubectl apply -f kubernetes/service.yaml
   ```
3. **Verify Liveness and Readiness**:
   Monitor rollout lifecycle status:
   ```bash
   kubectl rollout status deployment/sentinelflow-api
   kubectl get pods -l app=sentinelflow-api
   ```

---

## 5. Security & TLS Checklist

- **TLS Termination**: Configure an Ingress Controller (e.g. Nginx Ingress with cert-manager) in front of the Kubernetes service to terminate TLS, enforcing HTTPS on port 443.
- **CSP & HSTS Headers**: Handled natively by the FastAPI HTTP middleware to prevent XSS and clickjacking.
