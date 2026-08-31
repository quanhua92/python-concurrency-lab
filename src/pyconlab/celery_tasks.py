from .celery_app import celery_app
from .worker_task import execute_batch


@celery_app.task(name="pyconlab.multiply")
def multiply_task(
    job_count: int,
    size: int,
    seed: int,
) -> dict[str, int]:
    return execute_batch(
        num_jobs=job_count,
        size=size,
        seed=seed,
    )
