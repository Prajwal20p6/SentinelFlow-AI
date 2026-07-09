# Deployment Checkpoints & Validation Guide

Checkpoints checklist before deploying code to staging or production environments.

---

## 1. Pre-Deployment Checks
- `[ ]` Confirm all unit and integration tests are passing cleanly (`pytest`).
- `[ ]` Ensure code styling is validated with ESLint and PEP8 checkers.
- `[ ]` Check that JWT key variables are updated with randomized strings.
- `[ ]` Verify database connection string uses PostgreSQL adapter.

---

## 2. Deployment Steps
- `[ ]` Apply configmaps and secrets templates (`kubectl apply`).
- `[ ]` Apply deployments and service routing configs.
- `[ ]` Run DB migrations checklist (`alembic upgrade head`).
- `[ ]` Seed database default values.

---

## 3. Post-Deployment Verification
- `[ ]` Call the liveness check route (`GET /api/v1/health`).
- `[ ]` Verify that Prometheus scrapers harvest metrics on `/api/v1/metrics`.
- `[ ]` Trigger a dry-run anomaly and confirm incident is successfully mapped.
