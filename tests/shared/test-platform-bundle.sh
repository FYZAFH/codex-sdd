#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TMP_DIR="$(mktemp -d /tmp/double-sdd-bundle.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

python3 "${REPO_ROOT}/scripts/render-platform-bundle.py" \
    --platform codex \
    --output "${TMP_DIR}/codex" \
    --logical-root "${TMP_DIR}/codex"

test -f "${TMP_DIR}/codex/.agents/skills/using-double-sdd/SKILL.md"
test -f "${TMP_DIR}/codex/.agents/skills/subagent-driven-development/SKILL.md"
test -f "${TMP_DIR}/codex/.agents/skills/code-review/SKILL.md"
test -f "${TMP_DIR}/codex/.agents/skills/writing-plans/SKILL.md"
test -f "${TMP_DIR}/codex/.agents/skills/technical-direction-orchestrator/SKILL.md"
test -f "${TMP_DIR}/codex/.agents/skills/ui-design-reference/SKILL.md"
test -f "${TMP_DIR}/codex/.codex/agents/direction-worker-conductor.toml"
test -f "${TMP_DIR}/codex/.codex/agents/implementer.toml"
test -f "${TMP_DIR}/codex/.codex/agents/spec-code-reviewer.toml"
test -f "${TMP_DIR}/codex/.codex/agents/quality-code-reviewer.toml"
test -f "${TMP_DIR}/codex/.codex/agents/spec-document-reviewer.toml"
test -f "${TMP_DIR}/codex/.codex/agents/plan-document-reviewer.toml"
test -f "${TMP_DIR}/codex/.codex/agents/roundtable-participant.toml"
test -f "${TMP_DIR}/codex/.codex/config.toml"

grep -q "update_plan" "${TMP_DIR}/codex/.agents/skills/subagent-driven-development/SKILL.md"
grep -q "spawn_agent" "${TMP_DIR}/codex/.agents/skills/subagent-driven-development/SKILL.md"
grep -q "agent_type: implementer" "${TMP_DIR}/codex/.agents/skills/subagent-driven-development/SKILL.md"
grep -q "agent_type: spec-code-reviewer" "${TMP_DIR}/codex/.agents/skills/code-review/SKILL.md"
grep -q "agent_type: quality-code-reviewer" "${TMP_DIR}/codex/.agents/skills/code-review/SKILL.md"
grep -q "agent_type: spec-document-reviewer" "${TMP_DIR}/codex/.agents/skills/writing-specs/SKILL.md"
grep -q "agent_type: plan-document-reviewer" "${TMP_DIR}/codex/.agents/skills/writing-plans/SKILL.md"
grep -q 'follow the `code-review` skill' "${TMP_DIR}/codex/.agents/skills/subagent-driven-development/SKILL.md"
grep -q "Keep driving the plan forward until the entire plan is completed" "${TMP_DIR}/codex/.agents/skills/subagent-driven-development/SKILL.md"
grep -q "Launch both reviewers in parallel" "${TMP_DIR}/codex/.agents/skills/code-review/SKILL.md"
grep -q "do not act on quality feedback until spec has passed" "${TMP_DIR}/codex/.agents/skills/code-review/SKILL.md"
grep -q "Review output is input to evaluate, not an order to follow" "${TMP_DIR}/codex/.agents/skills/code-review/SKILL.md"
grep -q 'Use the `subagent-driven-development` skill' "${TMP_DIR}/codex/.agents/skills/writing-plans/SKILL.md"
grep -q 'ui-design-reference' "${TMP_DIR}/codex/.agents/skills/writing-specs/SKILL.md"
grep -q 'restrained industrial engineering-tool aesthetic' "${TMP_DIR}/codex/.agents/skills/ui-design-reference/SKILL.md"
grep -q "spawn_agent" "${TMP_DIR}/codex/.agents/skills/writing-specs/SKILL.md"
grep -q "spawn_agent" "${TMP_DIR}/codex/.agents/skills/writing-plans/SKILL.md"
grep -q 'Roundtable discussion requires pre-approved subagent use' "${TMP_DIR}/codex/.agents/skills/roundtable-discussion/SKILL.md"
grep -q 'Conservative Steward' "${TMP_DIR}/codex/.agents/skills/roundtable-discussion/agents/participant-prompts.md"
grep -q 'direction-worker-conductor' "${TMP_DIR}/codex/.agents/skills/technical-direction-orchestrator/SKILL.md"
grep -q 'verification-before-completion' "${TMP_DIR}/codex/.agents/skills/systematic-debugging/SKILL.md"
grep -q '^# double-sdd:managed$' "${TMP_DIR}/codex/.codex/agents/implementer.toml"
grep -q '^name = "direction-worker-conductor"$' "${TMP_DIR}/codex/.codex/agents/direction-worker-conductor.toml"
grep -q '^name = "implementer"$' "${TMP_DIR}/codex/.codex/agents/implementer.toml"
grep -q '^name = "spec-code-reviewer"$' "${TMP_DIR}/codex/.codex/agents/spec-code-reviewer.toml"
grep -q '^name = "quality-code-reviewer"$' "${TMP_DIR}/codex/.codex/agents/quality-code-reviewer.toml"
grep -q '^name = "spec-document-reviewer"$' "${TMP_DIR}/codex/.codex/agents/spec-document-reviewer.toml"
grep -q '^name = "plan-document-reviewer"$' "${TMP_DIR}/codex/.codex/agents/plan-document-reviewer.toml"
grep -q '^name = "roundtable-participant"$' "${TMP_DIR}/codex/.codex/agents/roundtable-participant.toml"
grep -q '^developer_instructions = ' "${TMP_DIR}/codex/.codex/agents/implementer.toml"
grep -q '^\[\[skills\.config\]\]$' "${TMP_DIR}/codex/.codex/agents/implementer.toml"
grep -Fq 'name = "skill-creator"' "${TMP_DIR}/codex/.codex/agents/implementer.toml"
grep -Fq 'name = "imagegen"' "${TMP_DIR}/codex/.codex/agents/implementer.toml"
grep -Fq 'name = "chrome:Chrome"' "${TMP_DIR}/codex/.codex/agents/implementer.toml"
grep -Fq "path = \"${TMP_DIR}/codex/.agents/skills/ui-design-reference/SKILL.md\"" "${TMP_DIR}/codex/.codex/agents/implementer.toml"
grep -Fq "path = \"${TMP_DIR}/codex/.agents/skills/technical-direction-orchestrator/SKILL.md\"" "${TMP_DIR}/codex/.codex/agents/direction-worker-conductor.toml"
grep -Fq "path = \"${TMP_DIR}/codex/.agents/skills/writing-specs/SKILL.md\"" "${TMP_DIR}/codex/.codex/agents/implementer.toml"
grep -Fq "path = \"${TMP_DIR}/codex/.agents/skills/writing-plans/SKILL.md\"" "${TMP_DIR}/codex/.codex/agents/quality-code-reviewer.toml"
grep -q '^approval_policy = "never"$' "${TMP_DIR}/codex/.codex/config.toml"
grep -q '^sandbox_mode = "danger-full-access"$' "${TMP_DIR}/codex/.codex/config.toml"
grep -q '^\[agents\]$' "${TMP_DIR}/codex/.codex/config.toml"
grep -q '^max_threads = 8$' "${TMP_DIR}/codex/.codex/config.toml"
grep -q '^max_depth = 3$' "${TMP_DIR}/codex/.codex/config.toml"
grep -q '^\[agents\.implementer\]$' "${TMP_DIR}/codex/.codex/config.toml"
grep -q '^config_file = "\./agents/implementer.toml"$' "${TMP_DIR}/codex/.codex/config.toml"
grep -q '^\[agents\.direction-worker-conductor\]$' "${TMP_DIR}/codex/.codex/config.toml"
grep -q '^config_file = "\./agents/direction-worker-conductor.toml"$' "${TMP_DIR}/codex/.codex/config.toml"
grep -q '^\[agents\.spec-document-reviewer\]$' "${TMP_DIR}/codex/.codex/config.toml"
grep -q '^config_file = "\./agents/spec-document-reviewer.toml"$' "${TMP_DIR}/codex/.codex/config.toml"
grep -q '^\[agents\.roundtable-participant\]$' "${TMP_DIR}/codex/.codex/config.toml"
grep -q '^config_file = "\./agents/roundtable-participant.toml"$' "${TMP_DIR}/codex/.codex/config.toml"

for pattern in \
    "bootstrap.md" \
    "Use Codex's native skills system" \
    "CLAUDE.md" \
    "Claude Code" \
    "Skill tool" \
    "Agent tool" \
    "TodoWrite" \
    "subagent_type" \
    "superpowers:" \
    "\\.claude-plugin" \
    "CLAUDE_PLUGIN_ROOT" \
    "@ syntax" \
    "@file" \
    "Task tool (general-purpose)" \
    "hooks/hooks\\.json" \
    "vendor_imports" \
    "codex-home" \
    "superpowers-lite"
do
    if rg -n "$pattern" -S "${TMP_DIR}/codex" >/dev/null; then
        echo "Codex bundle still contains forbidden pattern: $pattern" >&2
        exit 1
    fi
done
