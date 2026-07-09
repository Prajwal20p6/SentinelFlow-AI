#!/bin/bash
# SentinelFlow AI — Deployment Verification script
# Run immediately after standard Kubernetes or Docker deployments to test all interfaces.

set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"

echo "============================================================"
echo "    STARTING SENTINELFLOW DEPLOYMENT VERIFICATION"
echo "============================================================"

# 1. Check health
echo "1. Checking liveness and readiness probe routes..."
LIVENESS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/health")
READINESS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/ready")

if [ "$LIVENESS_CODE" -eq 200 ] && [ "$READINESS_CODE" -eq 200 ]; then
  echo "✓ Probes verification succeeded."
else
  echo "ERROR: Health check probes returned non-200. Liveness: $LIVENESS_CODE, Readiness: $READINESS_CODE"
  exit 1
fi

# 2. Check OpenAPI schema
echo "2. Fetching OpenAPI schema endpoint..."
OPENAPI_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/openapi.json")
if [ "$OPENAPI_CODE" -eq 200 ]; then
  echo "✓ OpenAPI schemas are successfully registered."
else
  echo "ERROR: OpenAPI endpoint failed: $OPENAPI_CODE"
  exit 1
fi

# 3. Check Prometheus metrics
echo "3. Querying Prometheus metrics stream..."
METRICS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/metrics")
if [ "$METRICS_CODE" -eq 200 ]; then
  echo "✓ Prometheus instrumentation metrics verified."
else
  echo "ERROR: Prometheus endpoint failed: $METRICS_CODE"
  exit 1
fi

echo "============================================================"
echo "DEPLOYMENT VERIFICATION PASSED SUCCESSFULLY"
echo "============================================================"
exit 0
