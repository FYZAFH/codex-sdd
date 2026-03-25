#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(pwd)"
SOURCE_REPO=""
REPO_URL="https://github.com/FYZAFH/codex-sdd.git"
REPO_REF="main"
CHECKOUT_DIR="${XDG_CACHE_HOME:-${HOME}/.cache}/double-sdd/repo"
ARTIFACT_ROOT=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [--project-root PATH] [--source-repo PATH] [--repo-url URL] [--repo-ref REF] [--checkout-dir PATH] [--artifact-root PATH]

Fetches the double-SDD Codex source bundle when needed, then installs the native
project-scoped Codex setup into the target project.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --project-root)
            PROJECT_ROOT="${2:?missing path for --project-root}"
            shift 2
            ;;
        --source-repo)
            SOURCE_REPO="${2:?missing path for --source-repo}"
            shift 2
            ;;
        --repo-url)
            REPO_URL="${2:?missing url for --repo-url}"
            shift 2
            ;;
        --repo-ref)
            REPO_REF="${2:?missing ref for --repo-ref}"
            shift 2
            ;;
        --checkout-dir)
            CHECKOUT_DIR="${2:?missing path for --checkout-dir}"
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
            echo "bootstrap-codex-project.sh: unknown argument: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd)"

ensure_checkout() {
    if [ -n "$SOURCE_REPO" ]; then
        SOURCE_REPO="$(cd "$SOURCE_REPO" && pwd)"
        printf '%s\n' "$SOURCE_REPO"
        return 0
    fi

    if ! command -v git >/dev/null 2>&1; then
        echo "bootstrap-codex-project.sh: git is required unless --source-repo is provided" >&2
        exit 1
    fi

    mkdir -p "$(dirname "$CHECKOUT_DIR")"

    if [ -d "${CHECKOUT_DIR}/.git" ]; then
        current_origin="$(git -C "$CHECKOUT_DIR" config --get remote.origin.url || true)"
        if [ -n "$current_origin" ] && [ "$current_origin" != "$REPO_URL" ]; then
            echo "bootstrap-codex-project.sh: checkout dir already points to a different origin: $current_origin" >&2
            exit 1
        fi

        git -C "$CHECKOUT_DIR" remote set-url origin "$REPO_URL"
        git -C "$CHECKOUT_DIR" fetch --depth 1 origin "$REPO_REF"
        git -C "$CHECKOUT_DIR" checkout --force FETCH_HEAD >/dev/null 2>&1
    elif [ -e "$CHECKOUT_DIR" ]; then
        echo "bootstrap-codex-project.sh: checkout path exists and is not a git repo: $CHECKOUT_DIR" >&2
        exit 1
    else
        git clone --depth 1 --branch "$REPO_REF" "$REPO_URL" "$CHECKOUT_DIR" >/dev/null 2>&1
    fi

    printf '%s\n' "$CHECKOUT_DIR"
}

SOURCE_ROOT="$(ensure_checkout)"

cmd=("${SOURCE_ROOT}/scripts/install-codex-project.sh" --project-root "$PROJECT_ROOT")
[ -n "$ARTIFACT_ROOT" ] && cmd+=(--artifact-root "$ARTIFACT_ROOT")

exec "${cmd[@]}"
