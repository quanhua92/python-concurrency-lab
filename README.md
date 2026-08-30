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
uv run --python 3.14 pyconlab
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
| 3.14.5 standard | interpreters | true | 0 | 0.000s |
| 3.14.7 free-threaded | single | false | 2534702284800 | 0.849s |
| 3.14.7 free-threaded | threads | false | 2534702284800 | 0.216s |
| 3.14.7 free-threaded | processes | false | 2534702284800 | 0.295s |
| 3.14.7 free-threaded | interpreters | false | 0 | 0.000s |

The single, thread, and process modes produce matching checksums across both
builds. The `interpreters` mode currently returns no results and is therefore
reported with a zero checksum.

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

Inspect the active interpreter directly:

```console
uv run runtime_status
```
