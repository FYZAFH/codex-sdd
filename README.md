# codex-sdd

Codex-native **double-SDD** workflow for Codex CLI.

For Chinese documentation, see [README.zh-CN.md](README.zh-CN.md).

Unlike the broader [superpowers](https://github.com/obra/superpowers) workflow kit, `codex-sdd` is intentionally narrowed to Codex-native execution: it turns planning, implementation, and review into explicit custom subagents such as `implementer`, `spec-code-reviewer`, and `quality-code-reviewer`, and anchors orchestration in Codex-specific primitives and layout like `.codex/config.toml`, `.codex/agents/*.toml`, `.agents/skills/*`, and subagent dispatch/review loops built around Codex's native agent model rather than compatibility abstractions. In exchange for that tighter fit, it deliberately drops parts of the original repository that exist to support less capable environments, such as fallback mechanisms like `execute_plan` for systems without native subagents or parallel implementation/review agents.

double-SDD means:
- Specification-Driven Development
- Subagent-Driven Development

This repository is Codex-only. It installs native Codex assets into:
- project scope: `.agents/skills/`, `.codex/config.toml`, `.codex/agents/`
- user scope: `~/.agents/skills/`, `~/.codex/config.toml`, `~/.codex/agents/`

## Workflow

```text
writing-specs -> writing-plans -> subagent-driven-development -> finishing-a-development-branch
```

- `writing-specs` clarifies requirements and writes the approved design spec
- `writing-plans` turns the spec into an execution plan
- `subagent-driven-development` runs one implementer task at a time, then parallel `spec-code-reviewer` + `quality-code-reviewer` passes for the same slice
- `finishing-a-development-branch` handles final verification and branch wrap-up

## Install

Requirements:
- macOS / Linux: `bash`, `python3`
- Windows: `PowerShell`, `Python 3`
- Bootstrap flows also require `git`

Project-local install, macOS / Linux:

```bash
cd ~/example_sound
bash <(curl -fsSL https://raw.githubusercontent.com/FYZAFH/codex-sdd/main/scripts/bootstrap-codex-project.sh)
codex
```

Project-local install, Windows PowerShell:

```powershell
cd ~\example_sound
irm https://raw.githubusercontent.com/FYZAFH/codex-sdd/main/scripts/bootstrap-codex-project.ps1 | iex
codex
```

Project-local uninstall:

```bash
./.double-sdd/uninstall
```

```powershell
.\.double-sdd\uninstall.ps1
```

Global install, macOS / Linux:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/FYZAFH/codex-sdd/main/scripts/bootstrap-codex-global.sh)
codex
```

Global install, Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/FYZAFH/codex-sdd/main/scripts/bootstrap-codex-global.ps1 | iex
codex
```

## Source Layout

- `codex/config.toml` - orchestrator instructions and registered subagents
- `codex/agents/implementer.toml` - one-task TDD implementer
- `codex/agents/spec-code-reviewer.toml` - slice-level spec compliance reviewer
- `codex/agents/quality-code-reviewer.toml` - slice-level engineering quality reviewer
- `codex/agents/spec-document-reviewer.toml` - spec document reviewer
- `codex/agents/plan-document-reviewer.toml` - plan document reviewer
- `codex/skills/*/SKILL.md` - Codex-native workflow skills
- `scripts/` - install, uninstall, bootstrap, and render helpers
- `tests/shared/` - install/render validation

## Validation

```bash
python3 -m py_compile scripts/render-platform-bundle.py scripts/codex_installer.py
bash tests/shared/test-platform-bundle.sh
bash tests/shared/test-codex-install.sh
bash tests/shared/test-codex-project-install.sh
```

## Notes

- Codex orchestration lives in `.codex/config.toml`, not `AGENTS.md`
- Installed subagents explicitly disable inherited skills through `[[skills.config]]`

## License

MIT License - see [LICENSE](LICENSE).
