# SentinelFlow AI — Troubleshooting Guide

Resolutions for common runtime errors and connectivity issues in production environments.

---

## 1. Issue: WebSocket Reconnection Loops / Session Limits Exceeded

### Symptoms
- Frontend client receives code `4003` disconnections.
- Console shows `Connection limit (5) reached for user` logs.

### Remediation
1. **Cause**: Multiple open tabs by the same authenticated user account exceed the 5 concurrent sessions safety cap.
2. **Action**:
   - Close inactive browser dashboard tabs.
   - Force session purge on the backend:
     ```bash
     # Purge redis user active sessions keys
     redis-cli del "user:sessions:admin@sentinelflow.ai"
     ```

---

## 2. Issue: Auto-Remediation Commands Stuck in `PENDING_APPROVAL`

### Symptoms
- Autopilot is enabled (`FF_CLOUD_REMEDIATION=true`), but critical incidents (e.g. CPU spikes) remain in state `PENDING_APPROVAL`.

### Remediation
1. **Cause**:
   - The LLM provider failover manager computed a confidence score lower than the 80% autopilot threshold.
   - The Enkrypt Safety Envelope engine matched the command against the threat signature block denylist (forcing manual sign-off).
2. **Action**:
   - Check the incident timeline forensics page (`GET /api/v1/incidents/{id}/forensics`) to read the exact safety block assessment rationale.
   - Manually approve execution through the Slack Block Kit buttons or directly in the Admin Dashboard command console.

---

## 3. Issue: Database Migrations Mismatch Error (Alembic)

### Symptoms
- Backend fails to start with logs showing:
  `sqlalchemy.exc.OperationalError: no such table: users` or schema mismatch warnings.

### Remediation
1. **Cause**: Database tables are out of sync with current SQLAlchemy models.
2. **Action**:
   Run Alembic migrate script:
   ```bash
   alembic upgrade head
   ```
   If using SQLite local testing mode and database is corrupted, rebuild:
   ```bash
   # Executes migrations from scratch
   python scripts/python/setup_databases.py
   ```
