import argparse
import time

from .interpreter_runner import run_interpreters
from .jobs import make_jobs
from .kernel import summarize
from .runners import run_processes, run_single, run_threads
from .runtime_status import build_kind, gil_enabled


def main() -> None:
    parser = argparse.ArgumentParser(prog="pyconlab")
    parser.add_argument(
        "--mode",
        choices=["single", "threads", "processes", "interpreters"],
        default="single",
    )
    parser.add_argument("--jobs", type=int, default=16)
    parser.add_argument("--size", type=int, default=120)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=100)

    args = parser.parse_args()

    jobs = make_jobs(args.jobs, args.size, args.seed)

    start = time.perf_counter()
    if args.mode == "interpreters":
        results = run_interpreters(jobs, args.workers)
    elif args.mode == "threads":
        results = run_threads(jobs, args.workers)
    elif args.mode == "processes":
        results = run_processes(jobs, args.workers)
    else:
        results = run_single(jobs)
    wall = time.perf_counter() - start
    summary = summarize(results)

    print(
        f"mode={args.mode} jobs={args.jobs} size={args.size} "
        f"workers={args.workers} seed={args.seed} "
        f"build={build_kind()} gil_enabled={gil_enabled()}"
    )

    print(
        f"checksum_total={summary['checksum_total']} "
        f"checksum_min={summary['checksum_min']} "
        f"checksum_max={summary['checksum_max']} "
    )
    print(f"wall={wall:.3f}s")


if __name__ == "__main__":
    main()
