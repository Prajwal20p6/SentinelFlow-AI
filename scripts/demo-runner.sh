#!/bin/bash
# SentinelFlow AI — Automated Demo Injection Scenario script
# Triggers simulation alerts via api to showcase incident transitions on dashboards.

set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"

echo "============================================================"
echo "    STARTING SENTINELFLOW DEMO INJECTION RUNNER"
echo "============================================================"
echo "Target Host: $API_URL"

# Login as admin to get auth credentials
echo "1. Authenticating as administrator user..."
AUTH_RESP=$(curl -s -X POST \
  -F "username=admin@sentinelflow.ai" \
  -F "password=admin123" \
  "$API_URL/api/v1/auth/login")

TOKEN=$(echo "$AUTH_RESP" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4 || echo "")

if [ -z "$TOKEN" ]; then
  echo "ERROR: Failed to authenticate. Response: $AUTH_RESP"
  exit 1
fi
echo "✓ Login succeeded. Token acquired."

# Trigger CPU Spike scenario (routes to manual approval)
echo "2. Triggering CPU Spike alert scenario (HITL Gate)..."
CPU_RESP=$(curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"scenario":"CPU_SPIKE"}' \
  "$API_URL/api/v1/demo/trigger")
echo "✓ Trigger response: $CPU_RESP"

# Trigger Disk Full scenario (auto-remediates)
echo "3. Triggering Storage Exhaustion alert scenario (Autopilot)..."
DISK_RESP=$(curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"scenario":"DISK_FULL"}' \
  "$API_URL/api/v1/demo/trigger")
echo "✓ Trigger response: $DISK_RESP"

echo "============================================================"
echo "DEMO SCENARIOS INJECTED SUCCESSFULLY"
echo "Check the dashboard to view real-time state changes."
echo "============================================================"
exit 0
