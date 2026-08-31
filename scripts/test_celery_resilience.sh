#!/usr/bin/env bash

set -euo pipefail

EXPECTED_CHECKSUM="1808144973440"
WORKER_LOG=$(mktemp)
WORKER_PID=""

cleanup() {
  if [[ -n "$WORKER_PID" ]] && kill -0 "$WORKER_PID" 2>/dev/null; then
    kill -TERM "$WORKER_PID" 2>/dev/null || true
  fi

  if [[ -n "$WORKER_PID" ]]; then
    wait "$WORKER_PID" 2>/dev/null || true
  fi

  rm -f "$WORKER_LOG"
}

trap cleanup EXIT

echo "== Queue task before worker starts =="
QUEUED_ID=$(uv run python -c 'from pyconlab.celery_tasks import multiply_task; print(multiply_task.apply_async(args=(8, 128, 100)).id)')
echo "job_id=$QUEUED_ID"
echo

echo "== Start worker =="
uv run celery -A pyconlab.celery_app worker --loglevel=INFO --concurrency=2 >"$WORKER_LOG" 2>&1 &
WORKER_PID=$!

WORKER_READY=false
for _ in {1..30}; do
  if uv run celery -A pyconlab.celery_app inspect ping --timeout=1 >/dev/null 2>&1; then
    WORKER_READY=true
    break
  fi
  sleep 0.2
done

[[ "$WORKER_READY" == true ]]
echo "worker_ready=true"
echo

echo "== Recover queued task =="
QUEUED_STATUS=""
for _ in {1..50}; do
  QUEUED_STATUS=$(uv run python -c "from celery.result import AsyncResult; from pyconlab.celery_app import celery_app; print(AsyncResult('$QUEUED_ID', app=celery_app).state)")
  echo "status=$QUEUED_STATUS"

  if [[ "$QUEUED_STATUS" == "SUCCESS" ]]; then
    QUEUED_CHECKSUM=$(uv run python -c "from celery.result import AsyncResult; from pyconlab.celery_app import celery_app; print(AsyncResult('$QUEUED_ID', app=celery_app).result['checksum_total'])")
    [[ "$QUEUED_CHECKSUM" == "$EXPECTED_CHECKSUM" ]]
    break
  fi

  sleep 0.2
done

[[ "$QUEUED_STATUS" == "SUCCESS" ]]
echo "PASS: queued task survived worker absence"
echo

echo "== Warm shutdown =="
SHUTDOWN_ID=$(uv run python -c 'from pyconlab.celery_tasks import multiply_task; print(multiply_task.apply_async(args=(1, 64, 100), kwargs={"fault": "hang", "hang_seconds": 2}).id)')
SHUTDOWN_STATUS=""
for _ in {1..50}; do
  SHUTDOWN_STATUS=$(uv run python -c "from celery.result import AsyncResult; from pyconlab.celery_app import celery_app; print(AsyncResult('$SHUTDOWN_ID', app=celery_app).state)")
  if [[ "$SHUTDOWN_STATUS" == "STARTED" ]]; then
    break
  fi
  sleep 0.2
done

[[ "$SHUTDOWN_STATUS" == "STARTED" ]]
kill -TERM "$WORKER_PID"
set +e
wait "$WORKER_PID"
WORKER_EXIT=$?
set -e
WORKER_PID=""

[[ "$WORKER_EXIT" == "0" ]]
FINAL_STATUS=$(uv run python -c "from celery.result import AsyncResult; from pyconlab.celery_app import celery_app; print(AsyncResult('$SHUTDOWN_ID', app=celery_app).state)")
[[ "$FINAL_STATUS" == "SUCCESS" ]]

echo "worker_exit=$WORKER_EXIT task_status=$FINAL_STATUS"
echo "PASS: warm shutdown completed the running task"
