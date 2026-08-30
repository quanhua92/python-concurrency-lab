import argparse
import threading
from concurrent.futures import ThreadPoolExecutor

from .runtime_status import build_kind, gil_enabled


class Metrics:
    def __init__(self) -> None:
        self.batches = 0
        self.jobs = 0
        self.checksum_total = 0
        self.checksum_max = 0

    def record(self, jobs: int, checksum: int) -> None:
        self.batches += 1
        self.jobs += jobs
        self.checksum_total += checksum

        if checksum > self.checksum_max:
            self.checksum_max = checksum

    def merge(self, other: "Metrics") -> None:
        self.batches += other.batches
        self.jobs += other.jobs
        self.checksum_total += other.checksum_total
        self.checksum_max = max(self.checksum_max, other.checksum_max)

    def snapshot(self) -> tuple[int, int, int, int]:
        return (self.batches, self.jobs, self.checksum_total, self.checksum_max)


class LockedMetrics(Metrics):
    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()

    def record(self, jobs: int, checksum: int) -> None:
        with self._lock:
            super().record(jobs, checksum)


def checksum_for(worker: int, update: int) -> int:
    return worker * 100_000 + update + 1


def expected(workers: int, updates: int) -> Metrics:
    result = Metrics()

    for worker in range(workers):
        for update in range(updates):
            result.record(jobs=1, checksum=checksum_for(worker, update))
    return result


def run_shared(metrics: Metrics, workers: int, updates: int) -> Metrics:
    barrier = threading.Barrier(workers)

    def worker(worker_id: int) -> None:
        barrier.wait()

        for update in range(updates):
            metrics.record(jobs=1, checksum=checksum_for(worker_id, update))

    threads = [
        threading.Thread(target=worker, args=(worker_id,))
        for worker_id in range(workers)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    return metrics


def run_racy(workers: int, updates: int) -> Metrics:
    return run_shared(Metrics(), workers, updates)


def run_locked(workers: int, updates: int) -> Metrics:
    return run_shared(LockedMetrics(), workers, updates)


def build_partial(worker_id: int, updates: int) -> Metrics:
    metrics = Metrics()

    for update in range(updates):
        metrics.record(jobs=1, checksum=checksum_for(worker_id, update))

    return metrics


def run_partials(workers: int, updates: int) -> Metrics:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(build_partial, worker_id, updates)
            for worker_id in range(workers)
        ]
        partials = [future.result() for future in futures]

    result = Metrics()
    for partial in partials:
        result.merge(partial)
    return result


STRATEGIES = {"racy": run_racy, "locked": run_locked, "partials": run_partials}


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--strategy", choices=STRATEGIES, default="racy")
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--updates", type=int, default=100_000)

    args = parser.parse_args()

    expected_result = expected(args.threads, args.updates)

    observed = STRATEGIES[args.strategy](args.threads, args.updates)

    print(f"strategy={args.strategy} threads={args.threads} updates={args.updates}")

    print(f"build={build_kind()} gil_enabled={gil_enabled()}")

    print(f"expected={expected_result.snapshot()}")
    print(f"observed={observed.snapshot()}")

    clean = expected_result.snapshot() == observed.snapshot()

    print(f"clean={clean}")

    if not clean:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
