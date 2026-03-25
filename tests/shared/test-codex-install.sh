#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TEST_HOME="$(mktemp -d /tmp/double-sdd-codex-home.XXXXXX)"
trap 'rm -rf "$TEST_HOME"' EXIT

CODEX_HOME_DIR="${TEST_HOME}/custom-config/.codex"

mkdir -p "${CODEX_HOME_DIR}"
cat > "${CODEX_HOME_DIR}/AGENTS.md" <<'EOF'
Keep this line.
EOF
cat > "${CODEX_HOME_DIR}/config.toml" <<'EOF'
approval_policy = "on-request"

[existing]
answer = 42
EOF

HOME="$TEST_HOME" CODEX_HOME="${CODEX_HOME_DIR}" "${REPO_ROOT}/scripts/install-codex.sh"

test -f "${CODEX_HOME_DIR}/AGENTS.md"
grep -q "Keep this line." "${CODEX_HOME_DIR}/AGENTS.md"
if grep -q "double-sdd:start" "${CODEX_HOME_DIR}/AGENTS.md"; then
    echo "Codex install should not modify AGENTS.md" >&2
    exit 1
fi
test -d "${TEST_HOME}/.agents/skills/brainstorming"
test -d "${TEST_HOME}/.agents/skills/code-review"
grep -qx 'double-sdd' "${TEST_HOME}/.agents/skills/brainstorming/.double-sdd-owner"
grep -q 'agent_type: implementer' "${TEST_HOME}/.agents/skills/subagent-driven-development/SKILL.md"
test -f "${CODEX_HOME_DIR}/agents/implementer.toml"
test -f "${CODEX_HOME_DIR}/agents/spec-code-reviewer.toml"
test -f "${CODEX_HOME_DIR}/agents/spec-document-reviewer.toml"
grep -q '^# double-sdd:managed$' "${CODEX_HOME_DIR}/agents/implementer.toml"
grep -q '^\[\[skills\.config\]\]$' "${CODEX_HOME_DIR}/agents/implementer.toml"
grep -Fq "path = \"${TEST_HOME}/.agents/skills/brainstorming/SKILL.md\"" "${CODEX_HOME_DIR}/agents/implementer.toml"
grep -q 'approval_policy = "on-request"' "${CODEX_HOME_DIR}/config.toml"
grep -q '^\[existing\]$' "${CODEX_HOME_DIR}/config.toml"
grep -q '^answer = 42$' "${CODEX_HOME_DIR}/config.toml"
grep -q '^# double-sdd:codex-config-root:start$' "${CODEX_HOME_DIR}/config.toml"
grep -q '^# double-sdd:codex-config-agents:start$' "${CODEX_HOME_DIR}/config.toml"
grep -q '^compact_prompt = """$' "${CODEX_HOME_DIR}/config.toml"
grep -q '^config_file = "\./agents/implementer.toml"$' "${CODEX_HOME_DIR}/config.toml"

HOME="$TEST_HOME" CODEX_HOME="${CODEX_HOME_DIR}" "${REPO_ROOT}/scripts/uninstall-codex.sh"

if [ -e "${TEST_HOME}/.agents/skills/brainstorming" ]; then
    echo "brainstorming skill still exists after uninstall" >&2
    exit 1
fi

if [ -e "${CODEX_HOME_DIR}/agents/implementer.toml" ]; then
    echo "implementer subagent still exists after uninstall" >&2
    exit 1
fi

grep -q "Keep this line." "${CODEX_HOME_DIR}/AGENTS.md"
if grep -q "double-sdd:start" "${CODEX_HOME_DIR}/AGENTS.md"; then
    echo "AGENTS.md should stay untouched after uninstall" >&2
    exit 1
fi

grep -q 'approval_policy = "on-request"' "${CODEX_HOME_DIR}/config.toml"
grep -q '^\[existing\]$' "${CODEX_HOME_DIR}/config.toml"
grep -q '^answer = 42$' "${CODEX_HOME_DIR}/config.toml"
if grep -q "double-sdd:codex-config" "${CODEX_HOME_DIR}/config.toml"; then
    echo "managed config block still exists after uninstall" >&2
    exit 1
fi
