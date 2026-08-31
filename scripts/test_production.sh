#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8124}"

echo "== Ping =="
curl -s "$BASE_URL/ping" | jq
echo


echo "== Submit normal job =="
NORMAL_RESPONSE=$(
  curl -s -X POST \
    "$BASE_URL/jobs?job_count=8&size=128&seed=100"
)

echo "$NORMAL_RESPONSE" | jq

NORMAL_ID=$(
  echo "$NORMAL_RESPONSE" | jq -r '.job_id'
)

echo "job_id=$NORMAL_ID"
echo


echo "== Poll normal job =="
while true; do
  RESPONSE=$(
    curl -s "$BASE_URL/jobs/$NORMAL_ID"
  )

  STATUS=$(
    echo "$RESPONSE" | jq -r '.status'
  )

  echo "status=$STATUS"

  if [[ "$STATUS" == "done" ]]; then
    echo "$RESPONSE" | jq
    break
  fi

  if [[ "$STATUS" == "failed" || "$STATUS" == "timeout" ]]; then
    echo "$RESPONSE" | jq
    exit 1
  fi

  sleep 0.2
done

echo


echo "== Submit crash job =="
CRASH_RESPONSE=$(
  curl -s -X POST \
    "$BASE_URL/jobs?job_count=1&size=64&fault=crash"
)

echo "$CRASH_RESPONSE" | jq

CRASH_ID=$(
  echo "$CRASH_RESPONSE" | jq -r '.job_id'
)

sleep 0.5

curl -s "$BASE_URL/jobs/$CRASH_ID" | jq
echo

echo "== Submit timeout job =="

TIMEOUT_RESPONSE=$(
  curl -s -X POST \
    "$BASE_URL/jobs?job_count=1&size=64&fault=hang&hang_seconds=5"
)

echo "$TIMEOUT_RESPONSE" | jq

TIMEOUT_ID=$(
  echo "$TIMEOUT_RESPONSE" | jq -r '.job_id'
)

echo "job_id=$TIMEOUT_ID"
echo


echo "== Wait until job times out =="

while true; do
  RESPONSE=$(
    curl -s "$BASE_URL/jobs/$TIMEOUT_ID"
  )

  STATUS=$(
    echo "$RESPONSE" | jq -r '.status'
  )

  echo "status=$STATUS"

  if [[ "$STATUS" == "timeout" ]]; then
    echo "$RESPONSE" | jq
    break
  fi

  if [[ "$STATUS" == "done" || "$STATUS" == "failed" ]]; then
    echo "unexpected terminal state:"
    echo "$RESPONSE" | jq
    exit 1
  fi

  sleep 0.2
done

echo


echo "== Verify CPU work is still physically running =="

METRICS=$(
  curl -s "$BASE_URL/metrics"
)

echo "$METRICS" | jq

STUCK=$(
  echo "$METRICS" | jq -r '.stuck_slots'
)

if (( STUCK > 0 )); then
  echo "PASS: timed-out CPU work still occupies a slot"
else
  echo "WARNING: stuck slot already finished before we sampled"
fi

echo


echo "== Wait until timed-out CPU work really finishes =="

while true; do
  METRICS=$(
    curl -s "$BASE_URL/metrics"
  )

  STUCK=$(
    echo "$METRICS" | jq -r '.stuck_slots'
  )

  ACTIVE=$(
    echo "$METRICS" | jq -r '.active_cpu'
  )

  echo "stuck_slots=$STUCK active_cpu=$ACTIVE"

  if [[ "$STUCK" == "0" ]]; then
    break
  fi

  sleep 0.2
done

echo "PASS: underlying CPU work eventually finished"
echo


echo "== Backpressure test =="

for i in $(seq 1 20); do
  HTTP_CODE=$(
    curl -s \
      -o "/tmp/pyconlab-response-$i.json" \
      -w "%{http_code}" \
      -X POST \
      "$BASE_URL/jobs?job_count=8&size=180&seed=$((100 + i))"
  )

  printf "request=%02d http=%s\n" "$i" "$HTTP_CODE"

  if [[ "$HTTP_CODE" == "503" ]]; then
    echo "backpressure observed:"
    cat "/tmp/pyconlab-response-$i.json" | jq
  fi
done

echo


echo "== Metrics after load =="
curl -s "$BASE_URL/metrics" | jq
echo


echo "== Ping after failures/load =="
curl -s "$BASE_URL/ping" | jq
echo


echo "== Done =="
