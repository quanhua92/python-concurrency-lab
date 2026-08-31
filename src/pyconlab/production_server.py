from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
)

from .production import ProductionEngine
from .runtime_status import (
    build_kind,
    gil_enabled,
)


def create_app(
    *,
    executor_kind: str,
    workers: int,
    queue_size: int,
    timeout: float,
) -> FastAPI:

    engine = ProductionEngine(
        executor_kind=executor_kind,
        workers=workers,
        queue_size=queue_size,
        timeout=timeout,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await engine.start()

        print(
            f"executor={executor_kind} "
            f"workers={workers} "
            f"queue_size={queue_size} "
            f"timeout={timeout}"
        )

        print(f"build={build_kind()} gil_enabled={gil_enabled()}")

        yield

        await engine.shutdown()

    app = FastAPI(
        title="Python Concurrency Lab",
        lifespan=lifespan,
    )

    @app.post(
        "/jobs",
        status_code=202,
    )
    async def submit_job(
        job_count: Annotated[
            int,
            Query(ge=1, le=64),
        ] = 8,
        size: Annotated[
            int,
            Query(ge=1, le=256),
        ] = 128,
        seed: int = 100,
        fault: Literal[
            "none",
            "crash",
            "hang",
        ] = "none",
        hang_seconds: Annotated[
            float,
            Query(ge=0.1, le=30),
        ] = 5.0,
    ):
        try:
            return engine.submit(
                job_count=job_count,
                size=size,
                seed=seed,
                fault=fault,
                hang_seconds=hang_seconds,
            )

        except RuntimeError as exc:
            raise HTTPException(
                status_code=503,
                detail=str(exc),
            )

    @app.get("/jobs/{job_id}")
    async def get_job(
        job_id: int,
    ):
        record = engine.get_job(job_id)

        if record is None:
            raise HTTPException(
                status_code=404,
                detail="job not found",
            )

        return record

    @app.get("/metrics")
    async def metrics():
        return engine.metrics()

    @app.get("/ping")
    async def ping():
        return {
            "pong": True,
            "build": build_kind(),
            "gil_enabled": gil_enabled(),
        }

    return app


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--executor",
        choices=[
            "threads",
            "interpreters",
        ],
        default="interpreters",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=4,
    )

    parser.add_argument(
        "--queue-size",
        type=int,
        default=8,
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8124,
    )

    args = parser.parse_args()

    app = create_app(
        executor_kind=args.executor,
        workers=args.workers,
        queue_size=args.queue_size,
        timeout=args.timeout,
    )

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=args.port,
    )


if __name__ == "__main__":
    main()
