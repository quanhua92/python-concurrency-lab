import cProfile
import pstats
import sys
import threading
import time
import timeit
from collections import Counter

from .interpreter_runner import run_interpreters
from .jobs import make_jobs
from .runners import run_single, run_threads
from .runtime_status import build_kind, gil_enabled

PARALLEL_THRESHOLD = 1.5
SAMPLE_INTERVAL = 0.001


def repeated_timing(num_jobs: int, size: int, seed: int) -> None:
    jobs = make_jobs(num_jobs, size, seed)

    times = timeit.repeat(lambda: run_single(jobs), repeat=5, number=1)

    print("times=" + ", ".join(f"{value:.3f}s" for value in times))

    print(f"best={min(times):.3f}s")


def profile_cpu(num_jobs: int, size: int, seed: int) -> None:
    jobs = make_jobs(num_jobs, size, seed)

    profiler = cProfile.Profile()
    profiler.enable()

    run_single(jobs)

    profiler.disable()

    pstats.Stats(profiler).strip_dirs().sort_stats("tottime").print_stats(10)


class StackSampler:
    def __init__(
        self,
        thread_id: int,
        interval: float = SAMPLE_INTERVAL,
    ) -> None:
        self.thread_id = thread_id
        self.interval = interval
        self.samples: Counter[str] = Counter()
        self.stop = threading.Event()

        self.thread = threading.Thread(
            target=self._sample,
            daemon=True,
        )

    def _sample(self) -> None:
        while not self.stop.is_set():
            time.sleep(self.interval)

            frame = sys._current_frames().get(self.thread_id)

            if frame is not None:
                self.samples[frame.f_code.co_name] += 1

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop.set()
        self.thread.join()


def sample_cpu(
    jobs_count: int,
    size: int,
    seed: int,
) -> None:
    jobs = make_jobs(
        jobs_count,
        size,
        seed,
    )

    with StackSampler(threading.get_ident()) as sampler:
        run_single(jobs)

    total = sum(sampler.samples.values())

    for function, count in sampler.samples.most_common(10):
        percent = count / total * 100 if total else 0

        print(f"{function:<20} {percent:>6.1f}%")


def measure_cores(
    name: str,
    runner,
) -> None:
    cpu_start = time.process_time()
    wall_start = time.perf_counter()

    runner()

    cpu_seconds = time.process_time() - cpu_start

    wall_seconds = time.perf_counter() - wall_start

    cores_used = cpu_seconds / wall_seconds if wall_seconds else 0

    print(
        f"{name:<14} "
        f"cpu={cpu_seconds:.3f}s "
        f"wall={wall_seconds:.3f}s "
        f"cores={cores_used:.2f}"
    )


def core_experiment(
    jobs_count: int,
    size: int,
    seed: int,
    workers: int,
) -> None:
    jobs = make_jobs(
        jobs_count,
        size,
        seed,
    )

    print(f"build={build_kind()} gil_enabled={gil_enabled()}")

    measure_cores(
        "single",
        lambda: run_single(jobs),
    )

    measure_cores(
        "threads",
        lambda: run_threads(
            jobs,
            workers,
        ),
    )

    measure_cores(
        "interpreters",
        lambda: run_interpreters(
            jobs,
            workers,
        ),
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--tool",
        choices=[
            "time",
            "cprofile",
            "sample",
            "cores",
        ],
        default="cores",
    )

    parser.add_argument(
        "--jobs",
        type=int,
        default=16,
    )

    parser.add_argument(
        "--size",
        type=int,
        default=128,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=100,
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=4,
    )

    args = parser.parse_args()

    if args.tool == "time":
        repeated_timing(
            args.jobs,
            args.size,
            args.seed,
        )

    elif args.tool == "cprofile":
        profile_cpu(
            args.jobs,
            args.size,
            args.seed,
        )

    elif args.tool == "sample":
        sample_cpu(
            args.jobs,
            args.size,
            args.seed,
        )

    elif args.tool == "cores":
        core_experiment(
            args.jobs,
            args.size,
            args.seed,
            args.workers,
        )


if __name__ == "__main__":
    main()
