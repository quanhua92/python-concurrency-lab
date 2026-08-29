import sys


def gil_enabled() -> bool | None:
    probe = getattr(sys, "_is_gil_enabled", None)
    return probe() if probe is not None else None
