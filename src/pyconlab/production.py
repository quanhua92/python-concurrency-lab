import asyncio
import time
from concurrent.futures import Executor, InterpreterPoolExecutor, ThreadPoolExecutor
from typing import Any

from .worker_task import execute_batch


class BusyMeter:
    """
    Measure CPU time / wall time only while at least one CPU job
    is physically occupying the executor.
    """

    def __init__(self) -> None:
        self.active = 0

        self._wall_start = 0.0
        self._cpu_start = 0.0

        self.wall_total = 0.0
        self.cpu_total = 0.0

    def start(self) -> None:
        if self.active == 0:
            self._wall_start = time.perf_counter()
            self._cpu_start = time.process_time()

        self.active += 1

    def stop(self) -> None:
        self.active -= 1

        if self.active == 0:
            self.wall_total += time.perf_counter() - self._wall_start

            self.cpu_total += time.process_time() - self._cpu_start

    @property
    def effective_cores(self) -> float:
        if self.wall_total == 0:
            return 0.0

        return self.cpu_total / self.wall_total


class ProductionEngine:
    def __init__(
        self, executor_kind: str, workers: int, queue_size: int, timeout: float
    ) -> None:
        self.executor_kind = executor_kind
        self.workers = workers
        self.timeout = timeout
        self.queue: asyncio.Queue[int] = asyncio.Queue(maxsize=queue_size)

        self.jobs: dict[int, dict[str, Any]] = {}
        self.worker_tasks: list[asyncio.Task] = []

        self.next_job_id = 1
        self.draining = False

        self.accepted = 0
        self.rejected = 0
        self.completed = 0
        self.failed = 0
        self.timed_out = 0

        self.stuck_slots = 0

        self.busy = BusyMeter()

        self.executor = self._make_executor()

    def _make_executor(self) -> Executor:
        if self.executor_kind == "threads":
            return ThreadPoolExecutor(
                max_workers=self.workers,
                thread_name_prefix="pyconlab",
            )

        if self.executor_kind == "interpreters":
            return InterpreterPoolExecutor(
                max_workers=self.workers,
                thread_name_prefix="pyconlab-interpreter",
            )

        raise ValueError(f"unknown executor: {self.executor_kind}")

    async def start(self) -> None:
        self.worker_tasks = [
            asyncio.create_task(
                self._worker_loop(worker_id), name=f"cpu-worker-{worker_id}"
            )
            for worker_id in range(self.workers)
        ]

    def submit(
        self,
        *,
        job_count: int,
        size: int,
        seed: int,
        fault: str = "none",
        hang_seconds: float = 5.0,
    ) -> dict[str, Any]:

        if self.draining:
            self.rejected += 1
            raise RuntimeError("service is draining")

        job_id = self.next_job_id
        self.next_job_id += 1

        record = {
            "job_id": job_id,
            "status": "queued",
            "job_count": job_count,
            "size": size,
            "seed": seed,
            "fault": fault,
            "hang_seconds": hang_seconds,
            "result": None,
            "error": None,
            "submitted_at": time.time(),
            "started_at": None,
            "finished_at": None,
            "finished_after_timeout": False,
        }

        self.jobs[job_id] = record

        try:
            self.queue.put_nowait(job_id)

        except asyncio.QueueFull:
            del self.jobs[job_id]

            self.rejected += 1

            raise RuntimeError("queue is full")

        self.accepted += 1

        return dict(record)

    def get_job(
        self,
        job_id: int,
    ) -> dict[str, Any] | None:

        record = self.jobs.get(job_id)

        if record is None:
            return None

        return dict(record)

    async def _worker_loop(
        self,
        worker_id: int,
    ) -> None:

        while True:
            job_id = await self.queue.get()

            try:
                await self._run_one(
                    worker_id,
                    job_id,
                )

            finally:
                self.queue.task_done()

    async def _run_one(
        self,
        worker_id: int,
        job_id: int,
    ) -> None:

        record = self.jobs[job_id]

        record["status"] = "running"
        record["worker_id"] = worker_id
        record["started_at"] = time.time()

        try:
            future = self.executor.submit(
                execute_batch,
                record["job_count"],
                record["size"],
                record["seed"],
                record["fault"],
                record["hang_seconds"],
            )

        except Exception as exc:
            record["status"] = "failed"
            record["error"] = f"{type(exc).__name__}: {exc}"
            record["finished_at"] = time.time()

            self.failed += 1
            return

        self.busy.start()

        wrapped = asyncio.wrap_future(future)

        try:
            result = await asyncio.wait_for(
                asyncio.shield(wrapped),
                timeout=self.timeout,
            )

        except TimeoutError:
            await self._handle_timeout(
                record,
                wrapped,
            )

        except Exception as exc:
            record["status"] = "failed"
            record["error"] = f"{type(exc).__name__}: {exc}"
            record["finished_at"] = time.time()

            self.failed += 1

        else:
            record["status"] = "done"
            record["result"] = result
            record["finished_at"] = time.time()

            self.completed += 1

        finally:
            self.busy.stop()

    async def _handle_timeout(
        self,
        record: dict[str, Any],
        wrapped: asyncio.Future,
    ) -> None:

        record["status"] = "timeout"
        record["error"] = f"exceeded timeout of {self.timeout:.2f}s"
        record["finished_at"] = time.time()

        self.timed_out += 1
        self.stuck_slots += 1

        try:
            await asyncio.shield(wrapped)

        except Exception as exc:
            record["late_error"] = f"{type(exc).__name__}: {exc}"

        else:
            record["finished_after_timeout"] = True

        finally:
            self.stuck_slots -= 1

    def metrics(self) -> dict[str, Any]:
        return {
            "executor": self.executor_kind,
            "workers": self.workers,
            "queue_size": self.queue.maxsize,
            "queue_depth": self.queue.qsize(),
            "active_cpu": self.busy.active,
            "stuck_slots": self.stuck_slots,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "completed": self.completed,
            "failed": self.failed,
            "timed_out": self.timed_out,
            "draining": self.draining,
            "busy_wall_seconds": round(
                self.busy.wall_total,
                3,
            ),
            "busy_cpu_seconds": round(
                self.busy.cpu_total,
                3,
            ),
            "effective_cores": round(
                self.busy.effective_cores,
                2,
            ),
        }

    async def shutdown(self) -> None:
        self.draining = True

        print("draining jobs...", flush=True)

        await self.queue.join()

        for task in self.worker_tasks:
            task.cancel()

        await asyncio.gather(
            *self.worker_tasks,
            return_exceptions=True,
        )

        self.executor.shutdown(
            wait=True,
            cancel_futures=False,
        )

        print("drain complete", flush=True)
