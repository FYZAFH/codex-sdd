# double-SDD for Codex

This directory is the Codex-native source tree for the double-SDD workflow.

double-SDD means:
- Specification-Driven Development
- Subagent-Driven Development

Codex does not use `bootstrap.md` or `AGENTS.md` prompt injection for this workflow.
The Codex controller behavior lives in `.codex/config.toml`, and the custom subagents
live in `.codex/agents/*.toml`.

## Source Layout

- `config.toml` — project-level Codex settings plus registered subagents
- `agents/direction-worker-conductor.toml` — one delegated double-SDD task conductor
- `agents/implementer.toml` — TDD implementation subagent
- `agents/spec-code-reviewer.toml` — spec compliance reviewer for the current implementation slice
- `agents/quality-code-reviewer.toml` — engineering quality reviewer for the current implementation slice
- `agents/spec-document-reviewer.toml` — spec document reviewer
- `agents/plan-document-reviewer.toml` — plan document reviewer
- `agents/roundtable-participant.toml` — bounded roundtable discussion participant
- `skills/technical-direction-orchestrator/` — direction-level workflow orchestration skill
- `skills/` — Codex-native skills installed into `.agents/skills/`

## Installed Layout

Project install writes:
- `.agents/skills/...`
- `.codex/config.toml`
- `.codex/agents/*.toml`
- `.double-sdd/uninstall`
- `.double-sdd/uninstall.cmd`
- `.double-sdd/uninstall.ps1`

Global install writes:
- `~/.agents/skills/...`
- `${CODEX_HOME:-~/.codex}/config.toml`
- `${CODEX_HOME:-~/.codex}/agents/*.toml`

Every installed subagent disables double-SDD, Codex system, and common plugin
skills through `[[skills.config]]` entries, so reviewer and implementer agents
do not inherit unrelated main-session skills.

## Rendering

`scripts/render-platform-bundle.py --platform codex` renders this directory into the
native Codex filesystem layout shown above.
