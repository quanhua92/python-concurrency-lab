# Python Concurrency Lab — Full Test Guide

## Goal

Test the entire `python-concurrency-lab` repository and verify that all six phases behave as intended.

Do not rely on exact timing numbers. Focus on:

- correctness;
- expected concurrency behavior;
- failure handling;
- consistency across runtimes;
- no crashes or hangs;
- expected HTTP status codes;
- graceful shutdown.

The package is:

```text
pyconlab
```

The project uses:

```text
uv
```

Two important Python runtimes are available:

```text
Standard CPython:
  selected by the default `uv run` environment

Free-threaded CPython:
  /opt/homebrew/bin/python3.14t
```

---

# 1. Basic Repository Validation

Run:

```bash
uv sync
```

Then verify imports:

```bash
uv run python -c "import pyconlab; print('ok')"
```

Expected:

```text
ok
```

If tests exist:

```bash
uv run pytest
```

Report any failures.

---

# 2. Phase 1 — GIL, Threads, Processes

Run the same workload using all execution modes.

## Single

```bash
uv run pyconlab \
  --mode single \
  --jobs 16 \
  --size 120 \
  --workers 4 \
  --seed 100
```

## Threads

```bash
uv run pyconlab \
  --mode threads \
  --jobs 16 \
  --size 120 \
  --workers 4 \
  --seed 100
```

## Processes

```bash
uv run pyconlab \
  --mode processes \
  --jobs 16 \
  --size 120 \
  --workers 4 \
  --seed 100
```

Verify:

```text
single checksum == threads checksum == processes checksum
```

Expected performance shape on standard CPython:

```text
single   ≈ baseline
threads  ≈ single
processes faster than single
```

Do not fail the test based solely on noisy timing differences.

The important result is:

```text
threads do not show strong CPU scaling under the standard GIL
processes can use multiple cores
```

---

# 3. Phase 2 — Async Server Responsiveness

Start:

```bash
uv run async_server
```

Run the server in a separate terminal; it remains running until stopped.

Assume:

```text
http://localhost:8123
```

Verify:

```bash
curl -s http://localhost:8123/ping
```

Expected HTTP 200.

Test inline CPU execution:

```bash
curl -s \
  "http://localhost:8123/multiply?count=8&size=128&seed=100&offload=false"
```

Test offloaded CPU execution:

```bash
curl -s \
  "http://localhost:8123/multiply?count=8&size=128&seed=100&offload=true"
```

Verify:

```text
checksum results match
```

Do not expect `offload=true` to make one CPU-bound request dramatically faster.

The intended behavior is:

```text
offload=false
→ CPU work can block event-loop responsiveness

offload=true
→ CPU work runs in another thread
→ event loop remains more responsive
```

Also verify invalid oversized inputs are rejected by FastAPI validation.

Example:

```bash
curl -i \
  "http://localhost:8123/multiply?size=100000"
```

Expected:

```text
4xx validation response
```

---

# 4. Phase 3 — Free-Threading and Data Races

## Runtime status

Standard:

```bash
uv run runtime_status
```

Expected:

```text
build=standard
gil_enabled=True
```

Free-threaded:

```bash
uv run \
  --python /opt/homebrew/bin/python3.14t \
  runtime_status
```

Expected:

```text
build=free-threaded
gil_enabled=False
```

---

## Race test — standard build

Run:

```bash
uv run metrics_race \
  --strategy racy
```

The result may appear clean.

Do not assume this means the code is race-safe.

---

## Race test — free-threaded build

Run:

```bash
uv run \
  --python /opt/homebrew/bin/python3.14t \
  metrics_race \
  --strategy racy
```

Expected:

```text
clean=False
```

Typical observed values should differ from expected values.

Run more than once if necessary.

---

## Locked strategy

```bash
uv run \
  --python /opt/homebrew/bin/python3.14t \
  metrics_race \
  --strategy locked
```

Expected:

```text
clean=True
```

---

## Partials strategy

```bash
uv run \
  --python /opt/homebrew/bin/python3.14t \
  metrics_race \
  --strategy partials
```

Expected:

```text
clean=True
```

Main assertion:

```text
racy shared mutation breaks under free-threading

locking fixes it

per-thread partial state + serial merge fixes it
```

If `race_stress` exists, run it too:

```bash
uv run \
  --python /opt/homebrew/bin/python3.14t \
  race_stress
```

It must not leave a permanent hung process.

---

# 5. Phase 4 — Subinterpreters

Run using standard CPython.

```bash
uv run \
  pyconlab \
  --mode interpreters \
  --jobs 16 \
  --size 120 \
  --workers 4 \
  --seed 100
```

Verify:

```text
checksum matches single/process/thread runs
```

Expected performance shape:

```text
standard threads
→ little CPU scaling

processes
→ multicore

interpreters
→ multicore
```

---

## Explicit interpreter boundary

Run:

```bash
uv run interpreter_boundary
```

Verify:

1. a job can cross into another interpreter;
2. the worker computes the matmul;
3. a small result returns successfully;
4. full-result transfer is slower than a small summary transfer.

Expected conceptual result:

```text
summary transfer < full matrix transfer
```

Do not require a specific ratio.

---

# 6. Phase 5 — Profiling and Measurement

## Repeated timing

```bash
uv run profiling --tool time
```

Verify multiple timing samples are produced.

---

## cProfile

```bash
uv run profiling --tool cprofile
```

Verify:

```text
matmul
```

is one of the dominant CPU functions.

---

## Sampling

```bash
uv run profiling --tool sample
```

Verify the sampler identifies CPU-heavy functions such as:

```text
matmul
```

---

## Effective cores — standard build

```bash
uv run \
  profiling \
  --tool cores \
  --workers 4
```

Expected shape:

```text
single       ≈ 1 effective core
threads      ≈ 1 effective core
interpreters > 1 effective core
```

---

## Effective cores — free-threaded build

```bash
uv run \
  --python /opt/homebrew/bin/python3.14t \
  profiling \
  --tool cores \
  --workers 4
```

Expected:

```text
free-threaded threads > 1 effective core
```

---

# 7. Phase 6 — Production Service

There are two preferred configurations.

## Standard CPython + subinterpreters

```bash
uv run \
  production_server \
  --executor interpreters \
  --workers 4 \
  --queue-size 8 \
  --timeout 2 \
  --port 8124
```

## Free-threaded CPython + threads

```bash
uv run \
  --python /opt/homebrew/bin/python3.14t \
  production_server \
  --executor threads \
  --workers 4 \
  --queue-size 8 \
  --timeout 2 \
  --port 8124
```

Test both configurations if practical.

---

# 8. Production Functional Test

If present, run:

```bash
./scripts/test_production.sh
```

Run it from another terminal while a Phase 6 server is listening on port
`8124`.

Otherwise manually test the following.

## Ping

```bash
curl -s http://localhost:8124/ping
```

Expected:

```text
HTTP 200
pong=true
```

---

## Normal job

Submit:

```bash
curl -s -X POST \
  "http://localhost:8124/jobs?job_count=8&size=128&seed=100"
```

Capture `job_id`.

Poll:

```bash
curl -s \
  "http://localhost:8124/jobs/<job_id>"
```

Expected lifecycle:

```text
queued
→ running
→ done
```

Result must contain a checksum summary.

---

## Crash job

```bash
curl -s -X POST \
  "http://localhost:8124/jobs?job_count=1&size=64&fault=crash"
```

Expected:

```text
status=failed
```

and an error similar to:

```text
RuntimeError: intentional worker crash
```

Then verify:

```bash
curl -s http://localhost:8124/ping
```

still succeeds.

Assertion:

```text
job failure != service failure
```

---

# 9. Timeout Semantics

Submit:

```bash
curl -s -X POST \
  "http://localhost:8124/jobs?job_count=1&size=64&fault=hang&hang_seconds=5"
```

With server timeout set to:

```text
2 seconds
```

poll the job until:

```text
status=timeout
```

Immediately query:

```bash
curl -s http://localhost:8124/metrics
```

Expected temporarily:

```text
stuck_slots > 0
active_cpu > 0
```

Continue polling metrics.

Eventually:

```text
stuck_slots=0
active_cpu=0
```

This proves:

```text
logical timeout
does not imply
physical CPU cancellation
```

---

# 10. Backpressure

Use a small capacity if necessary:

```bash
uv run \
  --python /opt/homebrew/bin/python3.14t \
  production_server \
  --executor threads \
  --workers 2 \
  --queue-size 2 \
  --timeout 2 \
  --port 8124
```

Submit many CPU-heavy jobs quickly.

Expected:

```text
initial requests → HTTP 202
once workers + queue are saturated → HTTP 503
```

Expected error:

```text
queue is full
```

Metrics at saturation should approximately show:

```text
active_cpu == worker count
queue_depth == queue_size
```

---

# 11. Graceful Drain

Use the dedicated script:

```bash
./scripts/test_drain.sh
```

It should use its own port, currently:

```text
8125
```

It should start a dedicated server with:

```text
workers=2
queue_size=4
```

Then submit 4 long-running jobs.

Before shutdown, expected shape:

```text
active_cpu=2
queue_depth=2
```

The script sends:

```text
SIGTERM
```

Expected behavior:

```text
server process remains alive
while accepted work drains
```

Then:

```text
queued jobs finish
executor finishes
server exits normally
```

Expected test output:

```text
PASS: correct test server
PASS: server is still alive and draining
PASS: server exited after drain
```

If shutdown markers are checked, `production.py` should use:

```python
print("draining jobs...", flush=True)
print("drain complete", flush=True)
```

Expected log:

```text
draining jobs...
drain complete
```

---

# 12. Final Correctness Matrix

Produce a final report like:

```text
Repository/imports          PASS / FAIL

Phase 1
single                      PASS / FAIL
threads                     PASS / FAIL
processes                   PASS / FAIL
checksum equality           PASS / FAIL

Phase 2
async server                PASS / FAIL
input validation            PASS / FAIL
offload responsiveness      PASS / FAIL

Phase 3
runtime detection           PASS / FAIL
free-thread race            PASS / FAIL
locked correctness          PASS / FAIL
partials correctness        PASS / FAIL

Phase 4
InterpreterPoolExecutor     PASS / FAIL
checksum equality           PASS / FAIL
boundary experiment         PASS / FAIL

Phase 5
repeated timing             PASS / FAIL
cProfile                    PASS / FAIL
sampling                    PASS / FAIL
effective cores             PASS / FAIL

Phase 6
normal lifecycle            PASS / FAIL
failure isolation           PASS / FAIL
timeout semantics           PASS / FAIL
bounded queue               PASS / FAIL
503 backpressure            PASS / FAIL
service responsiveness      PASS / FAIL
graceful drain              PASS / FAIL
```

---

# 13. Important Testing Rules

Do not fail tests because exact runtime numbers differ.

Correctness and qualitative behavior matter more than exact speedups.

For example:

```text
3.1x vs 2.4x
```

is not a failure.

But:

```text
free-threaded racy state becomes corrupted
```

is expected.

Similarly:

```text
standard-thread runtime occasionally appears clean
```

is not evidence that the race is safe.

Always compare checksums when comparing execution strategies.

Never use extremely large matrix sizes.

Keep normal test sizes roughly:

```text
64–180
```

because naive matrix multiplication is:

```text
O(N³)
```

A size like:

```text
100000
```

must never be used.

---

# Final Expected Conclusion

If everything passes, the repo demonstrates:

```text
Phase 1
processes give CPU parallelism

Phase 2
async I/O and CPU offloading solve different problems

Phase 3
free-threaded Python gives thread CPU parallelism
but exposes shared-state races

Phase 4
subinterpreters give isolated multicore execution
inside one OS process

Phase 5
profiling and CPU/wall measurements prove the behavior

Phase 6
bounded queues, backpressure, failure handling,
timeouts, observability, and graceful draining
turn the execution model into a production-style service
```
