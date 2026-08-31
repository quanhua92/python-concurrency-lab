from typing import Literal

from .celery_app import celery_app
from .worker_task import execute_batch


@celery_app.task(bind=True, name="pyconlab.multiply")
def multiply_task(
    self,
    job_count: int,
    size: int,
    seed: int,
    fault: Literal["none", "crash", "hang"] = "none",
    hang_seconds: float = 5.0,
    retry_count: int = 0,
) -> dict[str, int]:
    if self.request.retries < retry_count:
        raise self.retry(
            exc=RuntimeError("intentional retry"),
            countdown=0,
            max_retries=retry_count,
        )

    return execute_batch(
        num_jobs=job_count,
        size=size,
        seed=seed,
        fault=fault,
        hang_seconds=hang_seconds,
    )
