from concurrent.futures import InterpreterPoolExecutor

from pyconlab.jobs import MatMulJob, MatMulResult
from pyconlab.kernel import run_jobs
from pyconlab.runners import chunk_jobs


def run_chunk(jobs: list[MatMulJob]) -> list[MatMulResult]:
    return run_jobs(jobs)


def run_interpreters(jobs: list[MatMulJob], workers: int) -> list[MatMulResult]:
    chunks = chunk_jobs(jobs, workers)
    with InterpreterPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_chunk, chunk) for chunk in chunks]
        results = [result for future in futures for result in future.result()]
    return sorted(results, key=lambda result: result.job_id)
