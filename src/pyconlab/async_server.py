import argparse
import asyncio
import time
from typing import Annotated

from fastapi import FastAPI, Query

from pyconlab.input_service import fetch_jobs
from pyconlab.kernel import run_jobs, summarize
from pyconlab.runtime_status import gil_enabled

app = FastAPI()


@app.get("/ping")
async def ping():
    return {"pong": True}


@app.get("/multiply")
async def multiply(
    count: Annotated[int, Query(ge=1, le=64)] = 8,
    size: Annotated[int, Query(ge=1, le=256)] = 128,
    seed: int = 100,
    offload: bool = True,
):

    io_start = time.perf_counter()

    jobs = await fetch_jobs(
        count=count,
        size=size,
        seed=seed,
    )

    io_seconds = time.perf_counter() - io_start

    cpu_start = time.perf_counter()

    if offload:
        results = await asyncio.to_thread(
            run_jobs,
            jobs,
        )
    else:
        results = run_jobs(jobs)

    cpu_seconds = time.perf_counter() - cpu_start

    summary = summarize(results)

    return {
        "jobs": jobs,
        "size": size,
        "seed": seed,
        **summary,
        "io_seconds": round(io_seconds, 3),
        "cpu_seconds": round(cpu_seconds, 3),
        "gil_enabled": gil_enabled(),
        "offload": offload,
    }


def main():
    import uvicorn

    parser = argparse.ArgumentParser(prog="pyconlab.async_server")
    parser.add_argument("--port", type=int, default=8123)

    args = parser.parse_args()

    uvicorn.run(
        "pyconlab.async_server:app", host="0.0.0.0", port=args.port, reload=False
    )


if __name__ == "__main__":
    main()
