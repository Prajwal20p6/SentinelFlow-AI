# SentinelFlow AI — Operational Runbooks

Operational instructions for system administrators managing the SentinelFlow AI engine.

---

## 1. Runbook: High HTTP 5xx Error Rates Alert

This runbook triggers when Prometheus registers elevated API Gateway errors (`HighErrorRate`).

### Diagnostic Checklists

1. **Verify Backend Container Status**:
   ```bash
   kubectl get pods -l app=sentinelflow-api
   kubectl logs -f deployment/sentinelflow-api --tail=100
   ```
2. **Database Connection Queries Pool Limit**:
   Check if SQLite/PostgreSQL is throttling connections:
   ```bash
   # In Postgres CLI
   SELECT count(*), state FROM pg_stat_activity GROUP BY state;
   ```
3. **Inspect Redis Stream / WebSocket Queue limits**:
   Check if memory limits are exceeded:
   ```bash
   redis-cli info memory
   ```

### Remediation Action Plan

1. **Scale API deployment pods**:
   If request traffic spikes, scale up worker counts:
   ```bash
   kubectl scale deployment sentinelflow-api --replicas=5
   ```
2. **Revert Regressive Rollout**:
   If errors started after a code release, rollback:
   ```bash
   kubectl rollout undo deployment/sentinelflow-api
   ```

---

## 2. Runbook: Database Disaster Recovery (DB Failure)

Follow this procedure if the main database suffers data loss or filesystem corruption.

### Recovery Execution Steps (RTO < 1 Hour, RPO < 5 Minutes)

1. **Locate latest backup**:
   List available database dump files stored locally or download from AWS S3:
   ```bash
   # From local storage
   ls -la /backups/postgres_*.sql
   
   # Download from production S3 bucket
   aws s3 ls s3://sentinelflow-backups-production/postgres/
   ```
2. **Suspend API Services Ingestion**:
   Scale the API replica sets to zero to prevent write operations during the restore:
   ```bash
   kubectl scale deployment sentinelflow-api --replicas=0
   ```
3. **Execute Restore Utility**:
   Run the restoration script specifying the target backup timestamp:
   ```bash
   # Syntax: ./restore.sh <timestamp> [--s3]
   ./scripts/restore.sh 20260707_120000 --s3
   ```
4. **Deploy database migrations**:
   ```bash
   alembic upgrade head
   ```
5. **Resume API Services Ingestion**:
   Scale backend nodes back to normal:
   ```bash
   kubectl scale deployment sentinelflow-api --replicas=3
   ```
6. **Verify System Integrity**:
   Run diagnostic checks to ensure connection availability:
   ```bash
   ./scripts/health-check.sh
   ```
