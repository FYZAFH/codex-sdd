#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PROJECT_ROOT="$(pwd)"
ARTIFACT_ROOT=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [--project-root PATH] [--artifact-root PATH]

Removes the native project-scoped Codex adaptation from the target project.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --project-root)
            PROJECT_ROOT="${2:?missing path for --project-root}"
            shift 2
            ;;
        --artifact-root)
            ARTIFACT_ROOT="${2:?missing path for --artifact-root}"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "uninstall-codex-project.sh: unknown argument: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "uninstall-codex-project.sh: Python 3 is required" >&2
    exit 1
fi

cmd=(
    "$PYTHON_BIN"
    "${SCRIPT_DIR}/codex_installer.py"
    uninstall-project
    --project-root "$PROJECT_ROOT"
)
[ -n "$ARTIFACT_ROOT" ] && cmd+=(--artifact-root "$ARTIFACT_ROOT")

exec "${cmd[@]}"
