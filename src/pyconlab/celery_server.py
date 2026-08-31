from __future__ import annotations

import argparse
from typing import Annotated, Literal

from celery.result import AsyncResult
from fastapi import FastAPI, Query

from .celery_app import celery_app
from .celery_tasks import multiply_task


app = FastAPI(title="Python Concurrency Lab - Celery")


@app.get("/ping")
async def ping() -> dict[str, bool]:
    return {"pong": True}


@app.post("/jobs", status_code=202)
async def submit_job(
    job_count: Annotated[int, Query(ge=1, le=64)] = 8,
    size: Annotated[int, Query(ge=1, le=256)] = 128,
    seed: int = 100,
    fault: Literal["none", "crash", "hang"] = "none",
    hang_seconds: Annotated[float, Query(ge=0.1, le=30)] = 5.0,
    retry_count: Annotated[int, Query(ge=0, le=3)] = 0,
    time_limit: Annotated[float | None, Query(ge=0.1, le=30)] = None,
) -> dict[str, str]:
    # Celery replaces the function with a task proxy at runtime; its typing
    # stubs do not expose the proxy's apply_async() method.
    task = multiply_task.apply_async(  # pyright: ignore[reportFunctionMemberAccess]
        args=(job_count, size, seed),
        kwargs={
            "fault": fault,
            "hang_seconds": hang_seconds,
            "retry_count": retry_count,
        },
        time_limit=time_limit,
    )

    return {
        "job_id": str(task.id),
        "status": "queued",
    }


@app.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, object]:
    task = AsyncResult(job_id, app=celery_app)

    response: dict[str, object] = {
        "job_id": job_id,
        "status": task.state,
        "result": None,
    }

    if task.successful():
        response["result"] = task.result
    elif task.failed():
        response["error"] = str(task.result)

    return response


def main() -> None:
    parser = argparse.ArgumentParser(prog="pyconlab.celery_server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8126)
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
