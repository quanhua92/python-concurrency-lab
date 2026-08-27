from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MatMulJob:
    job_id: int
    size: int
    seed: int


@dataclass(frozen=True, slots=True)
class MatMulResult:
    job_id: int
    size: int
    checksum: int


def make_jobs(num_jobs: int, size: int, seed: int) -> list[MatMulJob]:
    if num_jobs < 1:
        raise ValueError("num_jobs must be >= 1")
    if size < 1:
        raise ValueError("size must be >= 1")
    return [MatMulJob(job_id=i, size=size, seed=seed) for i in range(num_jobs)]
