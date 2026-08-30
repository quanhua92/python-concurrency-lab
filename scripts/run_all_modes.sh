#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$script_dir/.."

readonly PYTHON_BUILDS=("3.14" "3.14t")
readonly MODES=("single" "threads" "processes" "interpreters")

for python_build in "${PYTHON_BUILDS[@]}"; do
    for mode in "${MODES[@]}"; do
        printf '\n==> Python %s, mode=%s\n' "$python_build" "$mode"
        uv run --python "$python_build" pyconlab --mode "$mode"
    done
done
