#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_ROOT="$(pwd)"
ARTIFACT_ROOT=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [--project-root PATH] [--artifact-root PATH]

Installs the native project-scoped double-SDD bundle into the target Codex project:
- updates PROJECT_ROOT/.codex/config.toml
- installs custom subagents into PROJECT_ROOT/.codex/agents
- installs custom skills into PROJECT_ROOT/.agents/skills
- creates uninstall helpers in PROJECT_ROOT/.double-sdd
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
            echo "install-codex-project.sh: unknown argument: $1" >&2
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
    echo "install-codex-project.sh: Python 3 is required" >&2
    exit 1
fi

cmd=(
    "$PYTHON_BIN"
    "${SCRIPT_DIR}/codex_installer.py"
    install-project
    --repo-root "$REPO_ROOT"
    --project-root "$PROJECT_ROOT"
)
[ -n "$ARTIFACT_ROOT" ] && cmd+=(--artifact-root "$ARTIFACT_ROOT")

exec "${cmd[@]}"
