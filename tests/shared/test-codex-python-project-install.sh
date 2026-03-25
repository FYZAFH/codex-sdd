#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TEST_ROOT="$(mktemp -d /tmp/double-sdd-codex-python-project.XXXXXX)"
trap 'rm -rf "$TEST_ROOT"' EXIT

PROJECT_ROOT="${TEST_ROOT}/example_sound"
ARTIFACT_ROOT="${PROJECT_ROOT}/.double-sdd"
mkdir -p "$PROJECT_ROOT"

git -C "$PROJECT_ROOT" init >/dev/null 2>&1
cat > "${PROJECT_ROOT}/AGENTS.md" <<'EOF'
Keep this line.
EOF
mkdir -p "${PROJECT_ROOT}/.codex"
cat > "${PROJECT_ROOT}/.codex/config.toml" <<'EOF'
approval_policy = "on-request"

[existing]
answer = 42
EOF

python3 "${REPO_ROOT}/scripts/codex_installer.py" install-project \
    --repo-root "${REPO_ROOT}" \
    --project-root "${PROJECT_ROOT}"

test -f "${PROJECT_ROOT}/AGENTS.md"
grep -q "Keep this line." "${PROJECT_ROOT}/AGENTS.md"
if grep -q "double-sdd:start" "${PROJECT_ROOT}/AGENTS.md"; then
    echo "Codex install should not modify AGENTS.md" >&2
    exit 1
fi
test -d "${PROJECT_ROOT}/.agents/skills/brainstorming"
test -d "${PROJECT_ROOT}/.agents/skills/code-review"
grep -qx 'double-sdd' "${PROJECT_ROOT}/.agents/skills/brainstorming/.double-sdd-owner"
test -f "${PROJECT_ROOT}/.codex/agents/implementer.toml"
test -f "${PROJECT_ROOT}/.codex/agents/spec-code-reviewer.toml"
test -f "${PROJECT_ROOT}/.codex/agents/plan-document-reviewer.toml"
grep -q '^\[\[skills\.config\]\]$' "${PROJECT_ROOT}/.codex/agents/spec-code-reviewer.toml"
grep -Fq "path = \"${PROJECT_ROOT}/.agents/skills/code-review/SKILL.md\"" "${PROJECT_ROOT}/.codex/agents/spec-code-reviewer.toml"
grep -q 'approval_policy = "on-request"' "${PROJECT_ROOT}/.codex/config.toml"
grep -q '^\[existing\]$' "${PROJECT_ROOT}/.codex/config.toml"
grep -q '^answer = 42$' "${PROJECT_ROOT}/.codex/config.toml"
grep -q '^# double-sdd:codex-config-root:start$' "${PROJECT_ROOT}/.codex/config.toml"
grep -q '^# double-sdd:codex-config-agents:start$' "${PROJECT_ROOT}/.codex/config.toml"
test -x "${ARTIFACT_ROOT}/uninstall"
test -f "${ARTIFACT_ROOT}/uninstall.cmd"
test -f "${ARTIFACT_ROOT}/uninstall.ps1"
grep -q "# double-sdd:start" "${PROJECT_ROOT}/.git/info/exclude"
grep -q ".double-sdd/" "${PROJECT_ROOT}/.git/info/exclude"

generated_uninstall_output="$("${ARTIFACT_ROOT}/uninstall" 2>&1)"
printf '%s\n' "$generated_uninstall_output" | grep -q "Removing project-local double-SDD helpers"

if [ -e "${PROJECT_ROOT}/.agents/skills/brainstorming" ]; then
    echo "brainstorming skill still exists after generated uninstall" >&2
    exit 1
fi

if [ -e "${PROJECT_ROOT}/.codex/agents/implementer.toml" ]; then
    echo "implementer subagent still exists after generated uninstall" >&2
    exit 1
fi

if [ -e "${ARTIFACT_ROOT}" ]; then
    echo ".double-sdd still exists after generated uninstall" >&2
    exit 1
fi

if grep -q "double-sdd:start" "${PROJECT_ROOT}/AGENTS.md"; then
    echo "AGENTS.md should stay untouched after generated uninstall" >&2
    exit 1
fi

grep -q 'approval_policy = "on-request"' "${PROJECT_ROOT}/.codex/config.toml"
grep -q '^\[existing\]$' "${PROJECT_ROOT}/.codex/config.toml"
grep -q '^answer = 42$' "${PROJECT_ROOT}/.codex/config.toml"
if grep -q "double-sdd:codex-config" "${PROJECT_ROOT}/.codex/config.toml"; then
    echo "managed config block still exists after generated uninstall" >&2
    exit 1
fi

if grep -q "double-sdd:start" "${PROJECT_ROOT}/.git/info/exclude"; then
    echo "managed exclude block still exists after generated uninstall" >&2
    exit 1
fi

python3 "${REPO_ROOT}/scripts/codex_installer.py" install-project \
    --repo-root "${REPO_ROOT}" \
    --project-root "${PROJECT_ROOT}"

python3 "${REPO_ROOT}/scripts/codex_installer.py" uninstall-project \
    --project-root "${PROJECT_ROOT}"

if [ -e "${PROJECT_ROOT}/.agents/skills/brainstorming" ]; then
    echo "brainstorming skill still exists after uninstall" >&2
    exit 1
fi

if [ -e "${PROJECT_ROOT}/.codex/agents/implementer.toml" ]; then
    echo "implementer subagent still exists after uninstall" >&2
    exit 1
fi

if [ -e "${ARTIFACT_ROOT}" ]; then
    echo ".double-sdd still exists after uninstall" >&2
    exit 1
fi

if grep -q "double-sdd:start" "${PROJECT_ROOT}/AGENTS.md"; then
    echo "AGENTS.md should stay untouched after uninstall" >&2
    exit 1
fi

grep -q 'approval_policy = "on-request"' "${PROJECT_ROOT}/.codex/config.toml"
grep -q '^\[existing\]$' "${PROJECT_ROOT}/.codex/config.toml"
grep -q '^answer = 42$' "${PROJECT_ROOT}/.codex/config.toml"
if grep -q "double-sdd:codex-config" "${PROJECT_ROOT}/.codex/config.toml"; then
    echo "managed config block still exists after uninstall" >&2
    exit 1
fi

if grep -q "double-sdd:start" "${PROJECT_ROOT}/.git/info/exclude"; then
    echo "managed exclude block still exists after uninstall" >&2
    exit 1
fi
