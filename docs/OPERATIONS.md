# SentinelFlow AI — Operations Manual

This guide describes standard systems administration tasks, backup configurations, log rotation, and operational commands.

---

## 1. Environment Variable Configuration Options

All settings are configured via the `.env` file or environment variables in container namespaces:

- **LOG_LEVEL**: Logs verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
- **RATE_LIMIT_REQUESTS**: Limit requests/IP window (default 60 requests/min).
- **FF_DEMO_MODE**: Toggle simulator thread daemon (set `false` in production).
- **FF_MFA_REQUIRED**: Enforce dual-factor authentication on all API actions.
- **OTEL_ENABLED**: Enable OpenTelemetry collector tracing.

---

## 2. Backup Retention & Rotation Schedule

Database and Qdrant vector store backups are executed daily.

- **Storage Location**: Local `/backups` filesystem and replicated to the `s3://sentinelflow-backups-production` S3 bucket.
- **Backups Retention**: 30 days. Old snapshots are automatically purged by the cleanup daemon.
- **Verification cron setup**:
  Add this entry to your crontab to execute backups nightly at 2:00 AM:
  ```cron
  0 2 * * * /app/scripts/backup.sh >> /var/log/sentinelflow-backup.log 2>&1
  ```

---

## 3. Database Maintenance and Schema Migrations

When upgrading the SentinelFlow code:

1. **Perform snapshot backup**:
   ```bash
   ./scripts/backup.sh
   ```
2. **Apply Alembic upgrades**:
   ```bash
   alembic upgrade head
   ```
3. **Verify readiness status**:
   ```bash
   ./scripts/health-check.sh
   ```
