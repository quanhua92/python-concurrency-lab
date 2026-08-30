import argparse
import faulthandler
import threading
import time

from .metrics_race import STRATEGIES, expected


def run_stress(strategy: str, trials: int, threads: int, updates: int) -> None:
    expected_result = expected(threads, updates).snapshot()

    failures = 0
    for trial in range(1, trials + 1):
        observed = STRATEGIES[strategy](threads, updates).snapshot()

        clean = observed == expected_result

        print(f"trial={trial}/{trials} clean={clean}")

        if not clean:
            failures += 1
    print(f"failures={failures}")

    if failures:
        raise SystemExit(1)


def demo_hang() -> None:
    lock = threading.Lock()

    lock.acquire()

    def worker() -> None:
        print("worker: waiting for lock")
        lock.acquire()
        lock.release()

    thread = threading.Thread(target=worker, name="blocked-worker")
    thread.start()

    faulthandler.dump_traceback_later(1.0)

    thread.join(timeout=2.0)
    faulthandler.cancel_dump_traceback_later()

    print("main: releasing lock")
    lock.release()
    thread.join()
    print("done")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--strategy", choices=STRATEGIES, default="racy")

    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--updates", type=int, default=100_000)

    parser.add_argument("--demo-hang", action="store_true")

    args = parser.parse_args()
    faulthandler.enable()

    if args.demo_hang:
        demo_hang()
        return

    run_stress(args.strategy, args.trials, args.threads, args.updates)


if __name__ == "__main__":
    main()
