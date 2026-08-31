# Python Concurrency Lab

Experiments for learning Python concurrency with pure-Python matrix multiplication.
The lab reports whether it is running a standard or free-threaded CPython build,
including the current GIL status.

Requirements:

- Python 3.14
- [uv](https://docs.astral.sh/uv/)

## Run the benchmark

Run the default single-mode benchmark with the standard Python 3.14 build:

```console
uv run pyconlab
```

Run it with the Homebrew free-threaded build to compare behavior:

```console
uv run --python /opt/homebrew/bin/python3.14t pyconlab
```

The command prints the execution mode, build type, GIL status, checksums, and
elapsed time. Both builds should produce the same checksums; the free-threaded
build reports `gil_enabled=False` while the standard build reports
`gil_enabled=True`.

Example:

```text
mode=single jobs=16 size=120 workers=4 seed=100 build=free-threaded gil_enabled=False
checksum_total=2534702284800 checksum_min=158418892800 checksum_max=158418892800
wall=0.849s
```

Select a concurrency strategy with `--mode`:

```console
uv run pyconlab --mode single
uv run pyconlab --mode threads --workers 4
uv run pyconlab --mode processes --workers 4
uv run pyconlab --mode interpreters --workers 4
```

Available modes are `single`, `threads`, `processes`, and `interpreters`.

Run every mode with both Python builds. The script explicitly uses the
Homebrew free-threaded interpreter:

```console
./scripts/run_all_modes.sh
```

### Sample report

The following results were collected with the script’s defaults (`jobs=16`,
`size=120`, `workers=4`, `seed=100`):

| Python build | Mode | GIL enabled | Checksum total | Wall time |
| --- | --- | ---: | ---: | ---: |
| 3.14.5 standard | single | true | 2534702284800 | 0.748s |
| 3.14.5 standard | threads | true | 2534702284800 | 0.759s |
| 3.14.5 standard | processes | true | 2534702284800 | 0.255s |
| 3.14.5 standard | interpreters | true | 2534702284800 | 0.222s |
| 3.14.7 free-threaded | single | false | 2534702284800 | 0.849s |
| 3.14.7 free-threaded | threads | false | 2534702284800 | 0.216s |
| 3.14.7 free-threaded | processes | false | 2534702284800 | 0.295s |
| 3.14.7 free-threaded | interpreters | false | 2534702284800 | 0.342s |

The single, thread, process, and interpreter modes produce matching checksums
across both builds.

## Phase 4: subinterpreters

The `interpreters` mode uses `InterpreterPoolExecutor` to run the existing
`run_jobs()` matmul code in separate interpreter workers within one OS process:

```console
uv run pyconlab --mode interpreters --workers 4
uv run --python /opt/homebrew/bin/python3.14t pyconlab --mode interpreters --workers 4
```

The boundary demo compares sending a tiny summary with sending the full result
matrix across an interpreter boundary:

```console
uv run interpreter_boundary
uv run --python /opt/homebrew/bin/python3.14t interpreter_boundary
```

Example results for a 128x128 matrix and 20 crossings are below. Timings vary
by machine and run; the important result is that full-result transfer costs
more than summary transfer for a sufficiently large payload.

| Python build | Summary crossing | Full-matrix crossing | Full/summary |
| --- | ---: | ---: | ---: |
| 3.14.5 standard | 0.0143s | 0.0297s | 2.1x |
| 3.14.7 free-threaded | 0.0106s | 0.0167s | 1.6x |

The full matrix costs more to cross than the tiny summary, illustrating the
tradeoff between subinterpreter isolation and data-transfer overhead.

## Production-style worker service

`production_server` exposes a bounded asynchronous job queue backed by either
threads or subinterpreters. Jobs support normal execution, intentional worker
failure, and timeout testing:

```console
uv run --python /opt/homebrew/bin/python3.14t production_server \
  --executor interpreters --workers 4 --queue-size 8 --timeout 2 --port 8124
```

In another terminal, run the load and failure checks:

```console
./scripts/test_production.sh
```

The test verifies `/ping`, successful jobs, worker failures, timeout handling,
continued CPU work after a timeout, and queue backpressure (`503` when the
bounded queue is full). The verified free-threaded run reported
`build=free-threaded`, `gil_enabled=false`, `stuck_slots=1` while timed-out
work was still running, and `8` rejected requests during the load test.

Verify graceful shutdown separately with:

```console
./scripts/test_drain.sh
```

This script starts its own standard-Python server, submits four long-running
jobs, sends `SIGTERM`, and confirms the server stays alive until the queue is
drained and logs `draining jobs...` followed by `drain complete`. The scripts
require `curl` and `jq`.

## Phase 3: shared-state experiments

The race experiments use the same `Metrics` workload with three strategies:

```console
uv run --python /opt/homebrew/bin/python3.14t metrics_race --strategy racy
uv run --python /opt/homebrew/bin/python3.14t metrics_race --strategy locked
uv run --python /opt/homebrew/bin/python3.14t metrics_race --strategy partials
```

With the defaults (`threads=8`, `updates=100000`), the free-threaded runtime
exposed the shared-state race:

```text
expected=(800000, 800000, 320000400000, 800000)
observed=(262456, 425427, 159029018777, 800000)
clean=False
```

The `locked` and `partials` strategies both produced the expected result:

```text
observed=(800000, 800000, 320000400000, 800000)
clean=True
```

Stress results with 20 trials, 16 threads, and 100000 updates per thread:

| Strategy | Failures |
| --- | ---: |
| `racy` | 20 |
| `locked` | 0 |
| `partials` | 0 |

Run the stress test with:

```console
uv run --python /opt/homebrew/bin/python3.14t race_stress --strategy racy --trials 20 --threads 16 --updates 100000
uv run --python /opt/homebrew/bin/python3.14t race_stress --strategy locked --trials 20
uv run --python /opt/homebrew/bin/python3.14t race_stress --strategy partials --trials 20
```

The controlled blocked-thread demo confirms that `faulthandler` captures the
worker blocked at `lock.acquire()`, after which the main thread releases the
lock and the program exits normally:

```console
uv run --python /opt/homebrew/bin/python3.14t race_stress --demo-hang
```

## Free-threaded FastAPI compatibility

On macOS, `uv run --python 3.14t` may resolve to an old uv-managed beta such as
`CPython 3.14.0b4+freethreaded`. That interpreter is incompatible with the
current FastAPI/Pydantic stack and can fail during import with
`_eval_type() got an unexpected keyword argument 'prefer_fwd_module'`, followed
by an `AssertionError`.

Upgrading the packages does not change which interpreter uv selects. Install
the current Homebrew free-threaded build and pass its path explicitly:

```console
brew install python-freethreading
uv run --python /opt/homebrew/bin/python3.14t async_server
```

The working setup is:

| Build | Interpreter | GIL |
| --- | --- | ---: |
| Standard | Homebrew CPython 3.14.x | enabled |
| Free-threaded | `/opt/homebrew/bin/python3.14t` (CPython 3.14.7) | disabled |

The project currently uses FastAPI 0.141.1, Pydantic 2.13.5,
Pydantic Core 2.46.5, and Uvicorn 0.52.4.

## Phase 7: Celery and Redis

Phase 7 provides a deliberate alternative to the in-process Phase 6 service.
Celery handles task scheduling and job state, while Redis acts as both broker
and result backend. The existing `execute_batch()` workload is reused
unchanged.

Start Redis:

```console
docker compose up -d
```

In a second terminal, start a Celery worker:

```console
uv run celery -A pyconlab.celery_app worker --loglevel=INFO --concurrency=4
```

In a third terminal, start the separate Celery-backed API:

```console
uv run celery_server
```

The API listens on `http://localhost:8126`. Submit and inspect a job with:

```console
curl -s -X POST "http://localhost:8126/jobs?job_count=8&size=128&seed=100"
curl -s "http://localhost:8126/jobs/<job_id>"
```

The dedicated smoke test checks the API, `202` submission, Celery task
progress (`STARTED` to `SUCCESS`), checksum correctness, and `422` input
validation:

```console
./scripts/test_celery.sh
```

Phase 6 manually owns the queue and executor lifecycle. Phase 7 delegates
those concerns to Redis and Celery while keeping the CPU workload identical.

Inspect the active interpreter directly:

```console
uv run runtime_status
```

## Testing the Lab

For a complete end-to-end validation of all seven phases, including
standard CPython, free-threaded CPython, subinterpreters, profiling,
backpressure, timeouts, graceful shutdown, and Celery/Redis, see
[TESTING.md](TESTING.md).
