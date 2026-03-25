#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TEST_ROOT="$(mktemp -d /tmp/double-sdd-codex-bootstrap-global.XXXXXX)"
trap 'rm -rf "$TEST_ROOT"' EXIT

TEST_HOME="${TEST_ROOT}/home"
CODEX_HOME_DIR="${TEST_ROOT}/config/.codex"
SOURCE_REPO="${TEST_ROOT}/source-repo"
CACHE_DIR="${TEST_ROOT}/cache/repo"
mkdir -p "${CODEX_HOME_DIR}" "$SOURCE_REPO"

cat > "${CODEX_HOME_DIR}/AGENTS.md" <<'EOF'
Keep this line.
EOF

cp -R "${REPO_ROOT}/." "${SOURCE_REPO}"
rm -rf "${SOURCE_REPO}/.git"
git -C "$SOURCE_REPO" init >/dev/null 2>&1
git -C "$SOURCE_REPO" config user.name test >/dev/null 2>&1
git -C "$SOURCE_REPO" config user.email test@example.com >/dev/null 2>&1
git -C "$SOURCE_REPO" add . >/dev/null 2>&1
git -C "$SOURCE_REPO" commit -m "snapshot" >/dev/null 2>&1

HOME="$TEST_HOME" CODEX_HOME="${CODEX_HOME_DIR}" "${REPO_ROOT}/scripts/bootstrap-codex-global.sh" \
    --repo-url "$SOURCE_REPO" \
    --checkout-dir "$CACHE_DIR"

test -d "${CACHE_DIR}/.git"
test -f "${CODEX_HOME_DIR}/AGENTS.md"
grep -q "Keep this line." "${CODEX_HOME_DIR}/AGENTS.md"
if grep -q "double-sdd:start" "${CODEX_HOME_DIR}/AGENTS.md"; then
    echo "Codex bootstrap global install should not modify AGENTS.md" >&2
    exit 1
fi
test -d "${TEST_HOME}/.agents/skills/brainstorming"
test -d "${TEST_HOME}/.agents/skills/code-review"
test -f "${CODEX_HOME_DIR}/agents/implementer.toml"
test -f "${CODEX_HOME_DIR}/agents/spec-document-reviewer.toml"
test -f "${CODEX_HOME_DIR}/config.toml"
grep -q '^# double-sdd:managed$' "${CODEX_HOME_DIR}/agents/implementer.toml"
grep -q '^\[\[skills\.config\]\]$' "${CODEX_HOME_DIR}/agents/implementer.toml"
grep -Fq "path = \"${TEST_HOME}/.agents/skills/brainstorming/SKILL.md\"" "${CODEX_HOME_DIR}/agents/implementer.toml"
grep -q '^compact_prompt = """$' "${CODEX_HOME_DIR}/config.toml"
grep -q '^config_file = "\./agents/implementer.toml"$' "${CODEX_HOME_DIR}/config.toml"

HOME="$TEST_HOME" CODEX_HOME="${CODEX_HOME_DIR}" "${REPO_ROOT}/scripts/bootstrap-codex-global.sh" \
    --repo-url "$SOURCE_REPO" \
    --checkout-dir "$CACHE_DIR" \
    --uninstall

if [ -e "${TEST_HOME}/.agents/skills/brainstorming" ]; then
    echo "brainstorming skill still exists after uninstall" >&2
    exit 1
fi

if [ -e "${CODEX_HOME_DIR}/agents/implementer.toml" ]; then
    echo "implementer subagent still exists after uninstall" >&2
    exit 1
fi

if grep -q "double-sdd:codex-config" "${CODEX_HOME_DIR}/config.toml"; then
    echo "managed config block still exists after uninstall" >&2
    exit 1
fi
