import threading
from concurrent.futures import ProcessPoolExecutor

from pyconlab.jobs import MatMulJob, MatMulResult
from pyconlab.kernel import run_jobs


def chunk_jobs(jobs: list[MatMulJob], workers: int) -> list[list[MatMulJob]]:
    if workers < 1:
        raise ValueError("workers must be >= 1")
    worker_count = min(workers, len(jobs))
    if worker_count == 0:
        return []
    base, extra = divmod(len(jobs), worker_count)

    chunks = []
    start = 0
    for index in range(worker_count):
        count = base + (1 if index < extra else 0)
        chunks.append(jobs[start : start + count])
        start += count

    return chunks


def run_single(jobs: list[MatMulJob]) -> list[MatMulResult]:
    return run_jobs(jobs)


def run_threads(jobs: list[MatMulJob], workers: int) -> list[MatMulResult]:
    chunks = chunk_jobs(jobs, workers)
    parts: list[list[MatMulResult]] = [[] for _ in chunks]

    def worker(index: int, chunk: list[MatMulJob]) -> None:
        parts[index] = run_jobs(chunk)

    threads = [
        threading.Thread(target=worker, args=(index, chunk), name=f"matmul-{index}")
        for index, chunk in enumerate(chunks)
    ]
    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    return sorted(
        (result for part in parts for result in part), key=lambda result: result.job_id
    )


def run_processes(jobs: list[MatMulJob], workers: int) -> list[MatMulResult]:
    chunks = chunk_jobs(jobs, workers)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_single, chunk) for chunk in chunks]
        results = [result for future in futures for result in future.result()]

    return sorted(results, key=lambda result: result.job_id)
