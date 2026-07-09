#!/bin/bash
# SentinelFlow AI — Health Check script for deployment validation
# Tests core API liveness, database transaction connectivity, Redis cache, and Qdrant clusters status.

set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"

echo "============================================================"
echo "    SENTINELFLOW SYSTEM DIAGNOSTICS & HEALTH CHECK"
echo "============================================================"
echo "Target Host: $API_URL"

# 1. Check HTTP service availability
echo -n "Checking API Liveness endpoint... "
Liveness=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/health")
if [ "$Liveness" -eq 200 ]; then
  echo "SUCCESS (200 OK)"
else
  echo "FAIL (HTTP Code: $Liveness)"
  exit 1
fi

# 2. Check Database, Redis, and Vector DB readiness
echo -n "Checking API Readiness status... "
Readiness_Body=$(curl -s "$API_URL/api/v1/ready" || echo '{"status":"FAILED"}')
Readiness_Status=$(echo "$Readiness_Body" | grep -o '"status":"[^"]*"' | head -n1 | cut -d'"' -f4 || echo "FAILED")

if [ "$Readiness_Status" == "ready" ] || [ "$Readiness_Status" == "SUCCESS" ]; then
  echo "READY (Synced)"
  echo "Diagnostics Payload: $Readiness_Body"
else
  echo "FAILED"
  echo "Diagnostics Payload: $Readiness_Body"
  exit 1
fi

echo "============================================================"
echo "System Status: HEALTHY"
echo "============================================================"
exit 0
