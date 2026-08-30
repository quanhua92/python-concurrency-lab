import sys
import sysconfig


def build_kind() -> str:
    if sysconfig.get_config_var("Py_GIL_DISABLED"):
        return "free-threaded"
    return "standard"


def gil_enabled() -> bool | None:
    probe = getattr(sys, "_is_gil_enabled", None)
    return probe() if probe is not None else None


def main() -> None:
    print(f"python={sys.version.split()}")
    print(f"executable={sys.executable}")
    print(f"build={build_kind()}")
    print(f"gil_enabled={gil_enabled()}")


if __name__ == "__main__":
    main()
