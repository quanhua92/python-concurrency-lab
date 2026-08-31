import time

from .jobs import MatMulJob
from .kernel import run_jobs, summarize


def execute_batch(
    num_jobs: int, size: int, seed: int, fault: str = "none", hang_seconds: float = 5.0
) -> dict[str, int]:
    if fault == "crash":
        raise RuntimeError("intentional worker crash")

    if fault == "hang":
        _busy_wait(hang_seconds)

    jobs = [
        MatMulJob(job_id=job_id, size=size, seed=seed) for job_id in range(num_jobs)
    ]

    results = run_jobs(jobs)
    return summarize(results)


def _busy_wait(seconds: float) -> None:
    deadline = time.perf_counter() + seconds

    value = 1

    while time.perf_counter() < deadline:
        value = (value * 3 + 1) % 1_000_003
