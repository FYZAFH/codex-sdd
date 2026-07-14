#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TEST_ROOT="$(mktemp -d /tmp/double-sdd-codex-project.XXXXXX)"
trap 'rm -rf "$TEST_ROOT"' EXIT

PROJECT_ROOT="${TEST_ROOT}/example_sound"
ARTIFACT_ROOT="${PROJECT_ROOT}/.double-sdd"
mkdir -p "$PROJECT_ROOT"
mkdir -p "${ARTIFACT_ROOT}/scripts"

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
cat > "${ARTIFACT_ROOT}/scripts/keep.txt" <<'EOF'
keep
EOF
cat > "${ARTIFACT_ROOT}/scripts/__init__.py" <<'EOF'
# user package
EOF

"${REPO_ROOT}/scripts/install-codex-project.sh" --project-root "$PROJECT_ROOT"

test -f "${PROJECT_ROOT}/AGENTS.md"
grep -q "Keep this line." "${PROJECT_ROOT}/AGENTS.md"
if grep -q "double-sdd:start" "${PROJECT_ROOT}/AGENTS.md"; then
    echo "Codex install should not modify AGENTS.md" >&2
    exit 1
fi
test -d "${PROJECT_ROOT}/.agents/skills/writing-specs"
test -d "${PROJECT_ROOT}/.agents/skills/code-review"
grep -qx 'double-sdd' "${PROJECT_ROOT}/.agents/skills/writing-specs/.double-sdd-owner"
test -f "${PROJECT_ROOT}/.codex/agents/implementer.toml"
test -f "${PROJECT_ROOT}/.codex/agents/spec-code-reviewer.toml"
test -f "${PROJECT_ROOT}/.codex/agents/spec-document-reviewer.toml"
grep -q '^\[\[skills\.config\]\]$' "${PROJECT_ROOT}/.codex/agents/implementer.toml"
grep -Fq "path = \"${PROJECT_ROOT}/.agents/skills/writing-specs/SKILL.md\"" "${PROJECT_ROOT}/.codex/agents/implementer.toml"
grep -q 'approval_policy = "on-request"' "${PROJECT_ROOT}/.codex/config.toml"
grep -q '^\[existing\]$' "${PROJECT_ROOT}/.codex/config.toml"
grep -q '^answer = 42$' "${PROJECT_ROOT}/.codex/config.toml"
grep -q '^# double-sdd:codex-config-root:start$' "${PROJECT_ROOT}/.codex/config.toml"
grep -q '^# double-sdd:codex-config-agents:start$' "${PROJECT_ROOT}/.codex/config.toml"
test -x "${ARTIFACT_ROOT}/uninstall"
test -f "${ARTIFACT_ROOT}/uninstall.cmd"
test -f "${ARTIFACT_ROOT}/uninstall.ps1"
grep -qx 'keep' "${ARTIFACT_ROOT}/scripts/keep.txt"
grep -qx '# user package' "${ARTIFACT_ROOT}/scripts/__init__.py"
test -f "${ARTIFACT_ROOT}/scripts/double_sdd/__init__.py"
test -f "${ARTIFACT_ROOT}/scripts/double_sdd/setup_worktree.py"
test -f "${ARTIFACT_ROOT}/scripts/double_sdd/metadata.py"
test -f "${ARTIFACT_ROOT}/scripts/double_sdd/path_safety.py"
test ! -e "${ARTIFACT_ROOT}/scripts/install-codex-project.sh"
python3 "${ARTIFACT_ROOT}/scripts/double_sdd/setup_worktree.py" --help >/dev/null
grep -q 'python \.double-sdd/scripts/double_sdd/setup_worktree.py --branch <feature-branch>' "${PROJECT_ROOT}/.agents/skills/subagent-driven-development/SKILL.md"
if grep -q 'python scripts/double_sdd/setup_worktree.py' "${PROJECT_ROOT}/.agents/skills/subagent-driven-development/SKILL.md"; then
    echo "subagent-driven-development skill still points at repo-local setup helper" >&2
    exit 1
fi
grep -q "# double-sdd:start" "${PROJECT_ROOT}/.git/info/exclude"
grep -q ".double-sdd/" "${PROJECT_ROOT}/.git/info/exclude"

generated_uninstall_output="$("${ARTIFACT_ROOT}/uninstall" 2>&1)"
printf '%s\n' "$generated_uninstall_output" | grep -q "Removing project-local double-SDD helpers"

if [ -e "${PROJECT_ROOT}/.agents/skills/writing-specs" ]; then
    echo "writing-specs skill still exists after generated uninstall" >&2
    exit 1
fi

if [ -e "${PROJECT_ROOT}/.codex/agents/implementer.toml" ]; then
    echo "implementer subagent still exists after generated uninstall" >&2
    exit 1
fi

grep -q "Keep this line." "${PROJECT_ROOT}/AGENTS.md"
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

if [ -e "${ARTIFACT_ROOT}/scripts/double_sdd" ]; then
    echo "double_sdd helper package still exists after generated uninstall" >&2
    exit 1
fi
grep -qx 'keep' "${ARTIFACT_ROOT}/scripts/keep.txt"
grep -qx '# user package' "${ARTIFACT_ROOT}/scripts/__init__.py"

if grep -q "double-sdd:start" "${PROJECT_ROOT}/.git/info/exclude"; then
    echo "managed exclude block still exists after generated uninstall" >&2
    exit 1
fi

"${REPO_ROOT}/scripts/install-codex-project.sh" --project-root "$PROJECT_ROOT"
"${REPO_ROOT}/scripts/uninstall-codex-project.sh" --project-root "$PROJECT_ROOT"

if [ -e "${PROJECT_ROOT}/.agents/skills/writing-specs" ]; then
    echo "writing-specs skill still exists after uninstall" >&2
    exit 1
fi

if [ -e "${PROJECT_ROOT}/.codex/agents/implementer.toml" ]; then
    echo "implementer subagent still exists after uninstall" >&2
    exit 1
fi

if [ -e "${ARTIFACT_ROOT}/scripts/double_sdd" ]; then
    echo "double_sdd helper package still exists after uninstall" >&2
    exit 1
fi
grep -qx 'keep' "${ARTIFACT_ROOT}/scripts/keep.txt"
grep -qx '# user package' "${ARTIFACT_ROOT}/scripts/__init__.py"

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
