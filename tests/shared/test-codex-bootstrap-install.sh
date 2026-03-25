#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TEST_ROOT="$(mktemp -d /tmp/double-sdd-codex-bootstrap.XXXXXX)"
trap 'rm -rf "$TEST_ROOT"' EXIT

PROJECT_ROOT="${TEST_ROOT}/example_sound"
SOURCE_REPO="${TEST_ROOT}/source-repo"
CACHE_DIR="${TEST_ROOT}/cache/repo"
mkdir -p "$PROJECT_ROOT" "$SOURCE_REPO"

git -C "$PROJECT_ROOT" init >/dev/null 2>&1
cp -R "${REPO_ROOT}/." "${SOURCE_REPO}"
rm -rf "${SOURCE_REPO}/.git"
git -C "$SOURCE_REPO" init >/dev/null 2>&1
git -C "$SOURCE_REPO" config user.name test >/dev/null 2>&1
git -C "$SOURCE_REPO" config user.email test@example.com >/dev/null 2>&1
git -C "$SOURCE_REPO" add . >/dev/null 2>&1
git -C "$SOURCE_REPO" commit -m "snapshot" >/dev/null 2>&1

"${REPO_ROOT}/scripts/bootstrap-codex-project.sh" \
    --project-root "$PROJECT_ROOT" \
    --repo-url "$SOURCE_REPO" \
    --checkout-dir "$CACHE_DIR"

test -d "${CACHE_DIR}/.git"
test -d "${PROJECT_ROOT}/.agents/skills/brainstorming"
test -f "${PROJECT_ROOT}/.codex/agents/implementer.toml"
test -f "${PROJECT_ROOT}/.codex/agents/plan-document-reviewer.toml"
test -f "${PROJECT_ROOT}/.codex/config.toml"
test -x "${PROJECT_ROOT}/.double-sdd/uninstall"
if [ -e "${PROJECT_ROOT}/AGENTS.md" ]; then
    echo "bootstrap install should not create AGENTS.md" >&2
    exit 1
fi
grep -q '^\[\[skills\.config\]\]$' "${PROJECT_ROOT}/.codex/agents/implementer.toml"
grep -Fq "path = \"${PROJECT_ROOT}/.agents/skills/brainstorming/SKILL.md\"" "${PROJECT_ROOT}/.codex/agents/implementer.toml"
grep -q '^compact_prompt = """$' "${PROJECT_ROOT}/.codex/config.toml"
grep -q '^config_file = "\./agents/implementer.toml"$' "${PROJECT_ROOT}/.codex/config.toml"

"${PROJECT_ROOT}/.double-sdd/uninstall"

if [ -e "${PROJECT_ROOT}/.agents/skills/brainstorming" ]; then
    echo "brainstorming skill still exists after generated uninstall" >&2
    exit 1
fi

if [ -e "${PROJECT_ROOT}/.codex/agents/implementer.toml" ]; then
    echo "implementer subagent still exists after generated uninstall" >&2
    exit 1
fi

if grep -q "double-sdd:codex-config" "${PROJECT_ROOT}/.codex/config.toml"; then
    echo "managed config block still exists after generated uninstall" >&2
    exit 1
fi

if [ -e "${PROJECT_ROOT}/.double-sdd" ]; then
    echo ".double-sdd still exists after generated uninstall" >&2
    exit 1
fi

if grep -q "double-sdd:start" "${PROJECT_ROOT}/.git/info/exclude"; then
    echo "managed exclude block still exists after generated uninstall" >&2
    exit 1
fi
