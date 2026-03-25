#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
CODEX_HOME_DIR="${CODEX_HOME:-${HOME}/.codex}"

usage() {
    cat <<EOF
Usage: $(basename "$0") [--codex-home PATH]

Removes the native double-SDD bundle for Codex from:
- CODEX_HOME/config.toml
- CODEX_HOME/agents
- \$HOME/.agents/skills
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --codex-home)
            CODEX_HOME_DIR="${2:?missing path for --codex-home}"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "uninstall-codex.sh: unknown argument: $1" >&2
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
    echo "uninstall-codex.sh: Python 3 is required" >&2
    exit 1
fi

exec "$PYTHON_BIN" "${SCRIPT_DIR}/codex_installer.py" uninstall-global \
    --codex-home "$CODEX_HOME_DIR"
