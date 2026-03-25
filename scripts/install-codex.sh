#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CODEX_HOME_DIR="${CODEX_HOME:-${HOME}/.codex}"

usage() {
    cat <<EOF
Usage: $(basename "$0") [--codex-home PATH]

Installs the native double-SDD bundle for Codex:
- updates CODEX_HOME/config.toml
- installs custom subagents into CODEX_HOME/agents
- installs custom skills into \$HOME/.agents/skills
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
            echo "install-codex.sh: unknown argument: $1" >&2
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
    echo "install-codex.sh: Python 3 is required" >&2
    exit 1
fi

exec "$PYTHON_BIN" "${SCRIPT_DIR}/codex_installer.py" install-global \
    --repo-root "$REPO_ROOT" \
    --codex-home "$CODEX_HOME_DIR"
