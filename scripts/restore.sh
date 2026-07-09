#!/bin/bash
# SentinelFlow AI — Database and Vector Store Restore Script
# Restores PostgreSQL database and Qdrant storage folder from local/S3 snapshots.

set -euo pipefail

BACKUP_DIR="/backups"
S3_BUCKET="s3://sentinelflow-backups-production"

echo "============================================================"
echo "    STARTING SENTINELFLOW DB AND VECTOR STORE RESTORE"
echo "============================================================"

# Check if target parameters are supplied
if [ $# -lt 1 ]; then
  echo "Usage: $0 <backup-timestamp> [--s3]"
  echo "Example: $0 20260707_120000"
  exit 1
fi

TIMESTAMP=$1
USE_S3=${2:-""}

# 1. Download snapshot from S3 if requested
if [ "$USE_S3" == "--s3" ]; then
  if ! command -v aws &> /dev/null; then
    echo "ERROR: aws-cli is required to restore from S3."
    exit 1
  fi
  echo "Downloading backup snapshots from S3..."
  aws s3 cp "$S3_BUCKET/postgres/postgres_$TIMESTAMP.sql" "$BACKUP_DIR/"
  aws s3 cp "$S3_BUCKET/qdrant/qdrant_$TIMESTAMP.tar.gz" "$BACKUP_DIR/"
fi

# Validate file presence
if [ ! -f "$BACKUP_DIR/postgres_$TIMESTAMP.sql" ]; then
  echo "ERROR: Backup file $BACKUP_DIR/postgres_$TIMESTAMP.sql not found."
  exit 1
fi

# 2. Restore PostgreSQL
echo "Restoring PostgreSQL database..."
if [ -z "${DATABASE_URL:-}" ]; then
  echo "WARNING: DATABASE_URL not set. Restoring to local database."
  psql -U postgres -h localhost sentinelflow < "$BACKUP_DIR/postgres_$TIMESTAMP.sql"
else
  # Extract connection details or feed direct URI
  psql "$DATABASE_URL" < "$BACKUP_DIR/postgres_$TIMESTAMP.sql"
fi
echo "✓ Database restored successfully."

# 3. Restore Qdrant
if [ -f "$BACKUP_DIR/qdrant_$TIMESTAMP.tar.gz" ]; then
  echo "Restoring Qdrant vector storage directories..."
  mkdir -p /qdrant/storage
  tar -xzf "$BACKUP_DIR/qdrant_$TIMESTAMP.tar.gz" -C /qdrant/storage/
  echo "✓ Vector data structures recovered."
else
  echo "INFO: No Qdrant backup found for timestamp $TIMESTAMP. Skipping vector restore."
fi

# 4. Trigger database migrations checklist
echo "Running schema updates to ensure code sync..."
if [ -d "/app" ]; then
  cd /app
  alembic upgrade head
elif [ -d "../backend" ]; then
  cd ../backend
  venv/Scripts/python -m alembic upgrade head || python -m alembic upgrade head
fi

echo "============================================================"
echo "Restore operation finished successfully."
echo "============================================================"
