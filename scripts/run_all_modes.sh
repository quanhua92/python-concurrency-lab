#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$script_dir/.."

readonly PYTHON_BUILDS=("standard" "free-threaded")
readonly FREE_THREADED_PYTHON="/opt/homebrew/bin/python3.14t"
readonly MODES=("single" "threads" "processes" "interpreters")

for python_build in "${PYTHON_BUILDS[@]}"; do
    for mode in "${MODES[@]}"; do
        printf '\n==> Python %s, mode=%s\n' "$python_build" "$mode"
        if [[ "$python_build" == "free-threaded" ]]; then
            uv run --python "$FREE_THREADED_PYTHON" pyconlab --mode "$mode"
        else
            uv run pyconlab --mode "$mode"
        fi
    done
done
