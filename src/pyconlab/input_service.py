import asyncio

from pyconlab.jobs import MatMulJob

INPUT_LATENCY = 0.3


async def fetch_job(job_id: int, size: int, seed: int) -> MatMulJob:
    await asyncio.sleep(INPUT_LATENCY)

    return MatMulJob(job_id=job_id, size=size, seed=seed + job_id)


async def fetch_jobs_serial(count: int, size: int, seed: int) -> list[MatMulJob]:
    jobs = []
    for job_id in range(count):
        jobs.append(await fetch_job(job_id, size, seed))
    return jobs


async def fetch_jobs(count: int, size: int, seed: int) -> list[MatMulJob]:
    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(fetch_job(i, size, seed)) for i in range(count)]
    return [task.result() for task in tasks]


async def main() -> None:
    import time

    count, size, seed = 5, 32, 300

    start = time.perf_counter()
    serial = await fetch_jobs_serial(count, size, seed)
    serial_wall = time.perf_counter() - start

    start = time.perf_counter()
    concurrent = await fetch_jobs(count, size, seed)
    concurrent_wall = time.perf_counter() - start

    print(f"simulated input latency={INPUT_LATENCY}")
    print(f"serial={serial_wall:3f}s")
    print(f"concurrent={concurrent_wall:3f}s")
    print(
        f"speedup={serial_wall / concurrent_wall:.2f}x identical={serial == concurrent}"
    )


if __name__ == "__main__":
    asyncio.run(main())
