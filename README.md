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

Run it with the free-threaded build to compare behavior:

```console
uv run --python 3.14t pyconlab
```

The command prints the execution mode, build type, GIL status, checksums, and
elapsed time. Both builds should produce the same checksums; the free-threaded
build reports `gil_enabled=False` while the standard build reports
`gil_enabled=True`.

Example:

```text
mode=single jobs=16 size=120 workers=4 seed=100 build=free-threaded gil_enabled=False
checksum_total=2534702284800 checksum_min=158418892800 checksum_max=158418892800
wall=0.653s
```

Select a concurrency strategy with `--mode`:

```console
uv run pyconlab --mode single
uv run pyconlab --mode threads --workers 4
uv run pyconlab --mode processes --workers 4
uv run pyconlab --mode interpreters --workers 4
```

Available modes are `single`, `threads`, `processes`, and `interpreters`.

Run every mode with both Python builds:

```console
./scripts/run_all_modes.sh
```

### Sample report

The following results were collected with the script’s defaults (`jobs=16`,
`size=120`, `workers=4`, `seed=100`):

| Python build | Mode | GIL enabled | Checksum total | Wall time |
| --- | --- | ---: | ---: | ---: |
| 3.14.5 standard | single | true | 2534702284800 | 0.764s |
| 3.14.5 standard | threads | true | 2534702284800 | 0.765s |
| 3.14.5 standard | processes | true | 2534702284800 | 0.258s |
| 3.14.5 standard | interpreters | true | 0 | 0.000s |
| 3.14.0b4 free-threaded | single | false | 2534702284800 | 0.661s |
| 3.14.0b4 free-threaded | threads | false | 2534702284800 | 0.245s |
| 3.14.0b4 free-threaded | processes | false | 2534702284800 | 0.258s |
| 3.14.0b4 free-threaded | interpreters | false | 0 | 0.000s |

The single, thread, and process modes produce matching checksums across both
builds. The `interpreters` mode currently returns no results and is therefore
reported with a zero checksum.

Inspect the active interpreter directly:

```console
uv run runtime_status
```
