#!/bin/bash
# SentinelFlow AI — Database and Vector Store Backup Script
# Creates daily snapshots of PostgreSQL and Qdrant collections, uploads to AWS S3, and retains backups for 30 days.

set -euo pipefail

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
S3_BUCKET="s3://sentinelflow-backups-production"

mkdir -p "$BACKUP_DIR"

echo "============================================================"
echo "    STARTING SENTINELFLOW DB AND VECTOR RECOVERY BACKUP"
echo "============================================================"
echo "Timestamp: $TIMESTAMP"

# 1. Backup PostgreSQL
if [ -z "${DATABASE_URL:-}" ]; then
  echo "WARNING: DATABASE_URL not set. Attempting local pg_dump."
  pg_dump -U postgres -h localhost sentinelflow > "$BACKUP_DIR/postgres_$TIMESTAMP.sql"
else
  pg_dump "$DATABASE_URL" > "$BACKUP_DIR/postgres_$TIMESTAMP.sql"
fi
echo "✓ PostgreSQL backup generated successfully: postgres_$TIMESTAMP.sql"

# 2. Backup Qdrant storage folder
if [ -d "/qdrant/storage" ]; then
  tar -czf "$BACKUP_DIR/qdrant_$TIMESTAMP.tar.gz" -C /qdrant/storage .
  echo "✓ Qdrant storage snapshot compressed successfully: qdrant_$TIMESTAMP.tar.gz"
else
  echo "WARNING: /qdrant/storage not found. Skipping vector filesystem backup."
fi

# 3. Upload to AWS S3
if command -v aws &> /dev/null; then
  echo "Uploading snapshots to $S3_BUCKET..."
  aws s3 cp "$BACKUP_DIR/postgres_$TIMESTAMP.sql" "$S3_BUCKET/postgres/"
  if [ -f "$BACKUP_DIR/qdrant_$TIMESTAMP.tar.gz" ]; then
    aws s3 cp "$BACKUP_DIR/qdrant_$TIMESTAMP.tar.gz" "$S3_BUCKET/qdrant/"
  fi
  echo "✓ Snaps successfully archived to AWS S3 storage."
else
  echo "WARNING: aws-cli not found. Snapshots kept locally under $BACKUP_DIR."
fi

# 4. Clean up backups older than 30 days
find "$BACKUP_DIR" -type f -mtime +30 -delete
echo "✓ Old backups cleanup cycle finished (30 day retention)."

echo "============================================================"
echo "Backup cycle completed successfully: $TIMESTAMP"
echo "============================================================"
