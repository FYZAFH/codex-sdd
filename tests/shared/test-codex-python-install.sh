#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TEST_HOME="$(mktemp -d /tmp/double-sdd-codex-python-home.XXXXXX)"
trap 'rm -rf "$TEST_HOME"' EXIT

CODEX_HOME_DIR="${TEST_HOME}/custom-config/.codex"
SKILLS_ROOT="${TEST_HOME}/.agents/skills"
AGENTS_ROOT="${CODEX_HOME_DIR}/agents"
GLOBAL_ARTIFACT_ROOT="${TEST_HOME}/.double-sdd"
mkdir -p "$CODEX_HOME_DIR"
mkdir -p "${GLOBAL_ARTIFACT_ROOT}/scripts"

cat > "${CODEX_HOME_DIR}/AGENTS.md" <<'EOF'
Keep this line.
EOF
cat > "${CODEX_HOME_DIR}/config.toml" <<'EOF'
approval_policy = "on-request"

[existing]
answer = 42
EOF
cat > "${GLOBAL_ARTIFACT_ROOT}/scripts/keep.txt" <<'EOF'
keep
EOF
cat > "${GLOBAL_ARTIFACT_ROOT}/scripts/__init__.py" <<'EOF'
# user package
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
test -d "${SKILLS_ROOT}/writing-specs"
test -d "${SKILLS_ROOT}/code-review"
grep -qx 'double-sdd' "${SKILLS_ROOT}/writing-specs/.double-sdd-owner"
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
grep -qx 'keep' "${GLOBAL_ARTIFACT_ROOT}/scripts/keep.txt"
grep -qx '# user package' "${GLOBAL_ARTIFACT_ROOT}/scripts/__init__.py"
test -f "${GLOBAL_ARTIFACT_ROOT}/scripts/double_sdd/__init__.py"
test -f "${GLOBAL_ARTIFACT_ROOT}/scripts/double_sdd/setup_worktree.py"
test -f "${GLOBAL_ARTIFACT_ROOT}/scripts/double_sdd/metadata.py"
test -f "${GLOBAL_ARTIFACT_ROOT}/scripts/double_sdd/path_safety.py"
test ! -e "${GLOBAL_ARTIFACT_ROOT}/scripts/install-codex.sh"
python3 "${GLOBAL_ARTIFACT_ROOT}/scripts/double_sdd/setup_worktree.py" --help >/dev/null
grep -q '~/.double-sdd/scripts/double_sdd/setup_worktree.py' "${SKILLS_ROOT}/subagent-driven-development/SKILL.md"

HOME="$TEST_HOME" python3 "${REPO_ROOT}/scripts/codex_installer.py" uninstall-global \
    --codex-home "${CODEX_HOME_DIR}"

if [ -e "${SKILLS_ROOT}/writing-specs" ]; then
    echo "writing-specs skill still exists after uninstall" >&2
    exit 1
fi

if [ -e "${AGENTS_ROOT}/implementer.toml" ]; then
    echo "implementer subagent still exists after uninstall" >&2
    exit 1
fi

if [ -e "${GLOBAL_ARTIFACT_ROOT}/scripts/double_sdd" ]; then
    echo "global double_sdd helper package still exists after uninstall" >&2
    exit 1
fi
grep -qx 'keep' "${GLOBAL_ARTIFACT_ROOT}/scripts/keep.txt"
grep -qx '# user package' "${GLOBAL_ARTIFACT_ROOT}/scripts/__init__.py"

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
