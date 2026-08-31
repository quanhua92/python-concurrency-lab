#!/usr/bin/env bash
set -euo pipefail

PORT=8125
BASE_URL="http://localhost:$PORT"
LOG_FILE="/tmp/pyconlab-production-drain.log"

rm -f "$LOG_FILE"


echo "== Start server =="

uv run \
  --python /opt/homebrew/bin/python3.14 \
  production_server \
  --executor interpreters \
  --workers 2 \
  --queue-size 4 \
  --timeout 20 \
  --port "$PORT" \
  >"$LOG_FILE" 2>&1 &

SERVER_PID=$!

echo "server_pid=$SERVER_PID"
echo "port=$PORT"


cleanup() {
  if kill -0 "$SERVER_PID" 2>/dev/null; then
    kill -9 "$SERVER_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT


echo "== Wait for server =="

READY=false

for _ in $(seq 1 50); do
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "FAIL: server exited during startup"
    echo
    cat "$LOG_FILE"
    exit 1
  fi

  if curl -s "$BASE_URL/ping" >/dev/null 2>&1; then
    READY=true
    break
  fi

  sleep 0.2
done

if [[ "$READY" != "true" ]]; then
  echo "FAIL: server did not become ready"
  cat "$LOG_FILE"
  exit 1
fi

echo "server ready"
echo


echo "== Verify server configuration =="

METRICS=$(curl -s "$BASE_URL/metrics")

echo "$METRICS" | jq

WORKERS=$(echo "$METRICS" | jq -r '.workers')
QUEUE_SIZE=$(echo "$METRICS" | jq -r '.queue_size')

if [[ "$WORKERS" != "2" || "$QUEUE_SIZE" != "4" ]]; then
  echo "FAIL: connected to unexpected server configuration"
  exit 1
fi

echo "PASS: correct test server"
echo


echo "== Submit long-running jobs =="

JOB_IDS=()

for i in 1 2 3 4; do
  RESPONSE=$(
    curl -s -X POST \
      "$BASE_URL/jobs?job_count=1&size=64&fault=hang&hang_seconds=3"
  )

  JOB_ID=$(
    echo "$RESPONSE" | jq -r '.job_id'
  )

  JOB_IDS+=("$JOB_ID")

  echo "submitted job_id=$JOB_ID"
done

echo


echo "== State before shutdown =="

curl -s "$BASE_URL/metrics" | jq
echo


echo "== Send SIGTERM =="

kill -TERM "$SERVER_PID"

sleep 0.5


echo "== Check server is still alive while draining =="

if kill -0 "$SERVER_PID" 2>/dev/null; then
  echo "PASS: server is still alive and draining"
else
  echo "FAIL: server exited before drain completed"
  echo
  cat "$LOG_FILE"
  exit 1
fi

echo


echo "== Wait for graceful exit =="

while kill -0 "$SERVER_PID" 2>/dev/null; do
  echo "still draining..."
  sleep 0.5
done

echo "PASS: server exited after drain"
echo


echo "== Server log =="

cat "$LOG_FILE"
echo


echo "== Verify drain messages =="

if grep -q "draining jobs" "$LOG_FILE" &&
   grep -q "drain complete" "$LOG_FILE"; then

  echo "PASS: graceful drain completed"

else
  echo "FAIL: drain messages not found"
  exit 1
fi


trap - EXIT

echo
echo "== Done =="
