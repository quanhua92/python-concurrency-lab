from typing import Iterable

from pyconlab.jobs import MatMulJob, MatMulResult


def matrix_value(seed: int, row: int, col: int) -> int:
    """Return a deterministic small integer without using a RNG."""
    return (seed * (row + 1) * (col + 1)) % 10


def make_matrix(size: int, seed: int) -> list[list[int]]:
    return [
        [matrix_value(seed, row, col) for col in range(size)] for row in range(size)
    ]


def matmul(left: list[list[int]], right: list[list[int]]) -> list[list[int]]:
    """Naive O(n^3) matrix multiplication in Python bytecode."""
    rows = len(left)
    inner = len(left[0])
    cols = len(right[0])

    if rows == 0:
        return []
    if inner != len(right):
        raise ValueError("incompatible matrix dimensions")

    out = [[0] * cols for _ in range(rows)]

    for i in range(rows):
        for j in range(cols):
            total = 0
            for k in range(inner):
                total += left[i][k] * right[k][j]
            out[i][j] = total
    return out


def checksum(matrix: list[list[int]]) -> int:
    """Order-sensitive checksum"""
    acc = 0
    ordinal = 1
    for row in matrix:
        for value in row:
            acc += ordinal * value
            ordinal += 1
    return acc


def run_job(job: MatMulJob) -> MatMulResult:
    left = make_matrix(job.size, job.seed)
    right = make_matrix(job.size, job.seed + 1)

    product = matmul(left, right)

    return MatMulResult(job_id=job.job_id, size=job.size, checksum=checksum(product))


def run_jobs(jobs: Iterable[MatMulJob]) -> list[MatMulResult]:
    return [run_job(job) for job in jobs]


def summarize(results: Iterable[MatMulResult]) -> dict[str, int]:
    ordered = sorted(results, key=lambda result: result.job_id)
    if not ordered:
        return {"jobs": 0, "checksum_total": 0, "checksum_min": 0, "checksum_max": 0}

    checksums = [result.checksum for result in ordered]
    return {
        "jobs": len(ordered),
        "checksum_total": sum(checksums),
        "checksum_min": min(checksums),
        "checksum_max": max(checksums),
    }
