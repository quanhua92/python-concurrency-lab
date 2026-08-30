import threading
import time
from concurrent import interpreters

from pyconlab.kernel import checksum, make_matrix, matmul


def payload_worker(jobs, results, size: int, seed: int) -> None:
    left = make_matrix(size, seed)
    right = make_matrix(size, seed + 1)

    product = matmul(left, right)

    summary = (size, checksum(product))

    results.put(("ready", size))

    while True:
        command = jobs.get()

        if command is None:
            return

        mode, repeats = command

        if mode == "summary":
            payload = summary

        elif mode == "full":
            payload = product
        else:
            raise ValueError(mode)

        for _ in range(repeats):
            results.put(payload)


def payload_demo(size: int = 128, repeats: int = 20) -> None:
    interpreter = interpreters.create()

    jobs = interpreters.create_queue()
    results = interpreters.create_queue()

    interpreter.prepare_main(jobs=jobs, results=results, size=size, seed=100)

    worker = threading.Thread(
        target=interpreter.exec,
        args=(
            """
from pyconlab.interpreter_boundary import payload_worker

payload_worker(jobs, results, size, seed)
                """,
        ),
    )
    worker.start()
    print(results.get())

    times = {}

    for mode in ("summary", "full"):
        start = time.perf_counter()
        jobs.put((mode, repeats))
        for _ in range(repeats):
            _last = results.get()

        wall = time.perf_counter() - start
        times[mode] = wall
        print(f"{mode}: {wall:.4f}s ({wall / repeats * 1000:.3f} ms/crossing)")
    jobs.put(None)
    worker.join()
    interpreter.close()

    print(f"full/summary= {times['full'] / times['summary']:.1f}x")


def queue_demo() -> None:
    interpreter = interpreters.create()

    jobs = interpreters.create_queue()
    results = interpreters.create_queue()

    interpreter.prepare_main(jobs=jobs, results=results)

    worker = threading.Thread(
        target=interpreter.exec,
        args=(
            """
from pyconlab.jobs import MatMulJob
from pyconlab.kernel import run_job

while True:
    item = jobs.get()
    if item is None:
        break
    job_id, size, seed = item

    job = MatMulJob(job_id=job_id, size=size, seed=seed)

    result = run_job(job)
    results.put((result.job_id, result.size, result.checksum))
                """,
        ),
    )

    worker.start()

    jobs.put((0, 128, 100))
    result = results.get()
    print(f"result={result}")

    jobs.put(None)

    worker.join()
    interpreter.close()


def main() -> None:
    queue_demo()
    print()
    payload_demo()


if __name__ == "__main__":
    main()
