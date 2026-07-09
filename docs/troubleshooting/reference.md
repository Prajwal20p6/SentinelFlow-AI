# SentinelFlow AI — Troubleshooting & Maintenance Reference

This guide provides operators with solutions to common issues encountered during local development, demo runs, or production scaling.

---

## 1. Database Lock Errors (SQLite)

In local development, SQLite might report a database lock error (`database is locked` or `sqlite3.OperationalError: database is locked`) under concurrent workloads:

### Rationale
SQLite only allows one write transaction at a time. High-concurrency streams (like multiple simultaneous telemetry ingestion posts) can block each other.

### Mitigation
1. **Verify WAL Mode is Enabled**: The application core utilizes Write-Ahead Logging (WAL) by default to allow concurrent reads during a write. Check `app/core/database.py` to ensure the following lines execute:
   ```python
   cursor.execute("PRAGMA journal_mode=WAL")
   ```
2. **Increase Timeout**: Increase the database connection timeout to allow connections to wait for the write lock to clear:
   ```python
   connect_args = {"timeout": 30, "check_same_thread": False}
   ```
3. **Upgrade to PostgreSQL**: For multiple concurrent operators, upgrade the database connection to a PostgreSQL cluster (refer to [Production Deployment Reference](../deployment/production_reference.md)).

---

## 2. Alembic Migration Conflicts

When modifying schemas, Alembic may throw errors like `table already exists` or `KeyError: 'None'`:

### Rationale
- SQLite does not support transactional DDL. If a migration crashes halfway, the tables created before the crash will remain in the database file.
- The `down_revision` placeholder in templates must evaluate to a python literal `None` instead of a string `'None'`.

### Mitigation
1. **Clean Re-run (Local)**:
   - Delete the SQLite database: `Remove-Item backend/sentinelflow.db -Force`
   - Re-run migrations: `.\venv\Scripts\alembic.exe upgrade head`
2. **Fix Template Quoting**: Verify `script.py.mako` contains the following definition:
   ```python
   down_revision: Union[str, None] = ${repr(down_revision)}
   ```
   Instead of:
   ```python
   down_revision: Union[str, None] = '${down_revision}'
   ```

---

## 3. Cryptographic Audit Chain Failures

If the `/infra/audit-trail/verify` endpoint returns `valid: false`:

### Rationale
The SHA-256 block ledger forms a hash-chained sequence where each block incorporates the hash of the previous block:
`hash = SHA256(prev_hash : command : status : risk_score)`
If any record's `command_checked`, `status`, `risk_score`, or `hash` is manually changed or tampered with directly in the database, the validation fails.

### Mitigation
1. **Identify the Tampered Entry**: Look at the error response to identify the audit entry ID where the chain broke:
   ```json
   {
     "valid": false,
     "message": "Chain broken at audit #12. Expected a84f... got 29cf..."
   }
   ```
2. **Investigation**: Query the database to inspect the entry and compare it against historical server logs to identify the unauthorized mutation.
3. **Reset (Demo Mode Only)**: If testing, clear the audit trail to reset the genesis block:
   ```sql
   DELETE FROM audit_trails;
   ```

---

## 4. Qdrant / RAG Retrieval Failures

If semantic queries on runbooks fail to return any values:

### Rationale
The Qdrant collection might not have been seeded, or the local vector db directory `backend/data/qdrant/` is corrupted.

### Mitigation
1. **Force Re-seeding**:
   - Stop the backend server.
   - Delete the directory `backend/data/qdrant/`.
   - Start the backend server (`.\start.ps1`); the lifespan hook will automatically re-create the collection and seed standard runbook vectors.
