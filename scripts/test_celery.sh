#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8126}"
EXPECTED_CHECKSUM="1808144973440"

command -v curl >/dev/null
command -v jq >/dev/null

echo "== Ping =="
PING_CODE=$(curl -sS -o /tmp/pyconlab-celery-ping.json -w "%{http_code}" "$BASE_URL/ping")
cat /tmp/pyconlab-celery-ping.json | jq
[[ "$PING_CODE" == "200" ]]
echo

echo "== Submit job =="
SUBMIT_RESPONSE=$(curl -sS -X POST -w $'\n%{http_code}' \
  "$BASE_URL/jobs?job_count=8&size=128&seed=100")
SUBMIT_BODY=$(echo "$SUBMIT_RESPONSE" | sed '$d')
SUBMIT_CODE=$(echo "$SUBMIT_RESPONSE" | tail -n 1)
echo "$SUBMIT_BODY" | jq
[[ "$SUBMIT_CODE" == "202" ]]

JOB_ID=$(echo "$SUBMIT_BODY" | jq -r '.job_id')
[[ "$JOB_ID" != "null" && -n "$JOB_ID" ]]
echo "job_id=$JOB_ID"
echo

echo "== Poll job =="
JOB_STATUS=""
for attempt in {1..50}; do
  RESPONSE=$(curl -sS "$BASE_URL/jobs/$JOB_ID")
  JOB_STATUS=$(echo "$RESPONSE" | jq -r '.status')
  echo "status=$JOB_STATUS"

  if [[ "$JOB_STATUS" == "SUCCESS" ]]; then
    echo "$RESPONSE" | jq
    CHECKSUM=$(echo "$RESPONSE" | jq -r '.result.checksum_total')
    [[ "$CHECKSUM" == "$EXPECTED_CHECKSUM" ]]
    break
  fi

  if [[ "$JOB_STATUS" == "FAILURE" ]]; then
    echo "$RESPONSE" | jq
    exit 1
  fi

  sleep 0.2
done

[[ "$JOB_STATUS" == "SUCCESS" ]]
echo

echo "== Validation =="
INVALID_CODE=$(curl -sS -o /tmp/pyconlab-celery-invalid.json -w "%{http_code}" \
  -X POST "$BASE_URL/jobs?job_count=0")
cat /tmp/pyconlab-celery-invalid.json | jq
[[ "$INVALID_CODE" == "422" ]]

rm -f /tmp/pyconlab-celery-ping.json /tmp/pyconlab-celery-invalid.json
echo "PASS: Celery API checks"
