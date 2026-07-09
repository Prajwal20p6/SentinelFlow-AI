#!/bin/bash
# SentinelFlow AI — Concurrency Load Testing Runner script
# Runs parallel cURL processes to benchmark the API telemetry ingestion throughput.

set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
CONCURRENT_USERS=100
REQUESTS_PER_USER=10

echo "============================================================"
echo "    STARTING SENTINELFLOW CONCURRENCY LOAD TESTING"
echo "============================================================"
echo "Concurrent Users: $CONCURRENT_USERS"
echo "Requests per User: $REQUESTS_PER_USER"
echo "Target Endpoint: $API_URL/api/v1/telemetry/ingest"

# Function to execute requests sequentially
run_user_requests() {
  local user_id=$1
  for ((i=1; i<=REQUESTS_PER_USER; i++)); do
    curl -s -X POST \
      -H "Content-Type: application/json" \
      -d "{\"node_name\":\"load-test-node-$user_id\",\"cpu_usage\":45.5,\"memory_usage\":60.2}" \
      "$API_URL/api/v1/telemetry/ingest" > /dev/null
  done
}

export -f run_user_requests
export API_URL
export REQUESTS_PER_USER

START_TIME=$(date +%s.%N)

# Trigger concurrent loops
for ((u=1; u<=CONCURRENT_USERS; u++)); do
  run_user_requests "$u" &
done

# Wait for background jobs to complete
wait

END_TIME=$(date +%s.%N)
DURATION=$(echo "$END_TIME - $START_TIME" | bc)
TOTAL_REQS=$((CONCURRENT_USERS * REQUESTS_PER_USER))
RPS=$(echo "scale=2; $TOTAL_REQS / $DURATION" | bc)

echo "------------------------------------------------------------"
echo "            LOAD TESTING RUNTIME STATISTICS"
echo "------------------------------------------------------------"
echo "  Total Workload duration:  $DURATION seconds"
echo "  Total Ingested requests:  $TOTAL_REQS requests"
echo "  Average throughput rate:  $RPS requests/sec"
echo "============================================================"
