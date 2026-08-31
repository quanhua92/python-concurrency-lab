import os

from celery import Celery


celery_app = Celery(
    "pyconlab",
    broker=os.getenv("PYCONLAB_CELERY_BROKER", "redis://localhost:6379/0"),
    backend=os.getenv("PYCONLAB_CELERY_BACKEND", "redis://localhost:6379/1"),
    include=("pyconlab.celery_tasks",),
)

celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_transport_options={"visibility_timeout": 30},
)
