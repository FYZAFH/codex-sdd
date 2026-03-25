#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TEST_HOME="$(mktemp -d /tmp/double-sdd-codex-python-home.XXXXXX)"
trap 'rm -rf "$TEST_HOME"' EXIT

CODEX_HOME_DIR="${TEST_HOME}/custom-config/.codex"
SKILLS_ROOT="${TEST_HOME}/.agents/skills"
AGENTS_ROOT="${CODEX_HOME_DIR}/agents"
mkdir -p "$CODEX_HOME_DIR"

cat > "${CODEX_HOME_DIR}/AGENTS.md" <<'EOF'
Keep this line.
EOF
cat > "${CODEX_HOME_DIR}/config.toml" <<'EOF'
approval_policy = "on-request"

[existing]
answer = 42
EOF

HOME="$TEST_HOME" python3 "${REPO_ROOT}/scripts/codex_installer.py" install-global \
    --repo-root "${REPO_ROOT}" \
    --codex-home "${CODEX_HOME_DIR}"

test -f "${CODEX_HOME_DIR}/AGENTS.md"
grep -q "Keep this line." "${CODEX_HOME_DIR}/AGENTS.md"
if grep -q "double-sdd:start" "${CODEX_HOME_DIR}/AGENTS.md"; then
    echo "Codex install should not modify AGENTS.md" >&2
    exit 1
fi
test -d "${SKILLS_ROOT}/brainstorming"
test -d "${SKILLS_ROOT}/code-review"
grep -qx 'double-sdd' "${SKILLS_ROOT}/brainstorming/.double-sdd-owner"
test -f "${AGENTS_ROOT}/implementer.toml"
test -f "${AGENTS_ROOT}/spec-code-reviewer.toml"
test -f "${AGENTS_ROOT}/plan-document-reviewer.toml"
grep -q '^# double-sdd:managed$' "${AGENTS_ROOT}/implementer.toml"
grep -q '^\[\[skills\.config\]\]$' "${AGENTS_ROOT}/quality-code-reviewer.toml"
grep -Fq "path = \"${TEST_HOME}/.agents/skills/code-review/SKILL.md\"" "${AGENTS_ROOT}/quality-code-reviewer.toml"
grep -q 'approval_policy = "on-request"' "${CODEX_HOME_DIR}/config.toml"
grep -q '^\[existing\]$' "${CODEX_HOME_DIR}/config.toml"
grep -q '^answer = 42$' "${CODEX_HOME_DIR}/config.toml"
grep -q '^# double-sdd:codex-config-root:start$' "${CODEX_HOME_DIR}/config.toml"
grep -q '^# double-sdd:codex-config-agents:start$' "${CODEX_HOME_DIR}/config.toml"
grep -q '^config_file = "\./agents/implementer.toml"$' "${CODEX_HOME_DIR}/config.toml"

HOME="$TEST_HOME" python3 "${REPO_ROOT}/scripts/codex_installer.py" uninstall-global \
    --codex-home "${CODEX_HOME_DIR}"

if [ -e "${SKILLS_ROOT}/brainstorming" ]; then
    echo "brainstorming skill still exists after uninstall" >&2
    exit 1
fi

if [ -e "${AGENTS_ROOT}/implementer.toml" ]; then
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
